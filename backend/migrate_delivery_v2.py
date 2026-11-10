
from sqlalchemy import text

from app.core.database import Base, engine
from app.models.delivery_model import (
    DeliveryCity,
    DeliveryArea,
    DeliveryPincode,
    DeliveryCityAdmin,
    DeliveryStaffArea,
)

print("Database migration: Delivery v2")
print("Target database: servicehub")

# Existing records are counted, never deleted or modified.
with engine.connect() as connection:
    for table in (
        "delivery_staff",
        "delivery_orders",
        "delivery_status_logs",
    ):
        count = connection.execute(
            text(f"SELECT COUNT(*) FROM public.{table}")
        ).scalar_one()
        print(f"{table}: {count} existing records")

print("\nThis migration will add schema only.")
print("No existing records or tables will be deleted.")

confirmation = input("\nType APPLY to continue: ").strip()

if confirmation != "APPLY":
    print("Migration cancelled. No changes made.")
    raise SystemExit(0)

# STEP 1: Add the new enum value.
# This transaction commits before any use of the new enum value.
with engine.begin() as connection:
    connection.execute(text("""
        ALTER TYPE public.delivery_staff_role
        ADD VALUE IF NOT EXISTS 'area_admin'
    """))

print("STEP 1 OK: area_admin enum")

# STEP 2: Add nullable columns to the existing orders table.
with engine.begin() as connection:
    connection.execute(text("""
        ALTER TABLE public.delivery_orders
        ADD COLUMN IF NOT EXISTS pincode VARCHAR(6)
    """))

    connection.execute(text("""
        ALTER TABLE public.delivery_orders
        ADD COLUMN IF NOT EXISTS area_id INTEGER
    """))

    connection.execute(text("""
        ALTER TABLE public.delivery_orders
        ADD COLUMN IF NOT EXISTS city_id INTEGER
    """))

print("STEP 2 OK: delivery_orders columns")

# STEP 3: Create only the five new tables.
# Existing legacy tables are deliberately excluded.
Base.metadata.create_all(
    bind=engine,
    tables=[
        DeliveryCity.__table__,
        DeliveryArea.__table__,
        DeliveryPincode.__table__,
        DeliveryCityAdmin.__table__,
        DeliveryStaffArea.__table__,
    ],
)

print("STEP 3 OK: new hierarchy tables")

# STEP 4: Add foreign keys and indexes to old orders table.
constraints = [
    (
        "fk_delivery_orders_area_id_delivery_areas",
        "FOREIGN KEY (area_id) REFERENCES public.delivery_areas(id)",
    ),
    (
        "fk_delivery_orders_city_id_delivery_cities",
        "FOREIGN KEY (city_id) REFERENCES public.delivery_cities(id)",
    ),
]

with engine.begin() as connection:
    for name, definition in constraints:
        exists = connection.execute(text("""
            SELECT 1
            FROM pg_constraint
            WHERE conname = :name
              AND conrelid = 'public.delivery_orders'::regclass
        """), {"name": name}).first()

        if not exists:
            connection.execute(text(
                f"ALTER TABLE public.delivery_orders "
                f"ADD CONSTRAINT {name} {definition}"
            ))

    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_delivery_orders_pincode
        ON public.delivery_orders (pincode)
    """))

    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_delivery_orders_area_id
        ON public.delivery_orders (area_id)
    """))

    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_delivery_orders_city_id
        ON public.delivery_orders (city_id)
    """))

print("STEP 4 OK: foreign keys and indexes")

# STEP 5: Verify final schema and old record counts.
with engine.connect() as connection:
    print("\nFINAL DELIVERY TABLES:")

    tables = connection.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name LIKE 'delivery_%'
        ORDER BY table_name
    """))

    for row in tables:
        print(row[0])

    print("\nFINAL STAFF ENUM:")
    enum_values = connection.execute(text("""
        SELECT e.enumlabel
        FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        WHERE t.typname = 'delivery_staff_role'
        ORDER BY e.enumsortorder
    """))

    for row in enum_values:
        print(row[0])

    print("\nOLD RECORD COUNTS:")
    for table in (
        "delivery_staff",
        "delivery_orders",
        "delivery_status_logs",
    ):
        count = connection.execute(
            text(f"SELECT COUNT(*) FROM public.{table}")
        ).scalar_one()
        print(f"{table}: {count}")

print("\nDELIVERY V2 MIGRATION COMPLETED")
