import React, { useEffect, useMemo, useState } from 'react'
import {
  Activity, ArrowRight, BedDouble, CalendarDays, CheckCircle2, ChevronDown, CircleUserRound,
  ClipboardList, Clock, CreditCard, HeartPulse, Home, LogIn, LogOut, Menu, MessageCircle,
  Search, ShieldCheck, ShoppingBag, Stethoscope, Store, Utensils, UserPlus, X
} from 'lucide-react'
import { api, asArray, endpoints, getToken, labelOf, setToken } from './api.js'

const categories = [
  { id: 'services', title: 'Local Services', desc: 'Find trusted service providers', icon: Store, tone: 'mint' },
  { id: 'hotels', title: 'Hotels & Rooms', desc: 'Explore stays and room options', icon: BedDouble, tone: 'blue' },
  { id: 'restaurants', title: 'Restaurants', desc: 'Menus, tables and food orders', icon: Utensils, tone: 'orange' },
  { id: 'doctors', title: 'Doctors', desc: 'Find doctors and available slots', icon: Stethoscope, tone: 'pink' },
]
const navItems = [
  ['home', 'Overview', Home], ['services', 'Find services', Store], ['hotels', 'Hotel bookings', BedDouble],
  ['restaurants', 'Restaurants', Utensils], ['doctors', 'Doctors', Stethoscope],
  ['myactivity', 'My activity', ClipboardList], ['provider', 'Provider workspace', CircleUserRound]
]

function Button({ children, variant = 'primary', ...props }) {
  return <button className={`btn btn-${variant}`} {...props}>{children}</button>
}
function Field({ label, ...props }) {
  return <label className="field"><span>{label}</span><input {...props} /></label>
}
function SelectField({ label, options, ...props }) {
  return <label className="field"><span>{label}</span><select {...props}>{options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label>
}
function Modal({ title, onClose, children }) {
  return <div className="modal-backdrop" onMouseDown={e => e.target === e.currentTarget && onClose()}>
    <section className="modal"><div className="modal-head"><h2>{title}</h2><button className="icon-btn" onClick={onClose} aria-label="Close"><X size={20}/></button></div>{children}</section>
  </div>
}
function Notice({ notice, clear }) {
  if (!notice) return null
  return <div className={`notice ${notice.type || 'info'}`} role="status">{notice.message}<button onClick={clear} aria-label="Dismiss"><X size={16}/></button></div>
}
function Empty({ title = 'Nothing to show yet', text = 'Connect the backend and try again.' }) {
  return <div className="empty"><div className="empty-icon"><Search size={22}/></div><b>{title}</b><p>{text}</p></div>
}
function DataCard({ item, type, onAction }) {
  const title = labelOf(item, type === 'doctors' ? 'Doctor profile' : 'Service provider')
  const subtitle = item?.category || item?.specialization || item?.address || item?.description || 'Available on ServiceHub'
  const price = item?.price ?? item?.consultation_fee ?? item?.amount
  return <article className="data-card">
    <div className={`provider-avatar ${type}`}><span>{title.slice(0,1).toUpperCase()}</span></div>
    <div className="data-card-body"><div className="card-title-row"><h3>{title}</h3>{item?.verified && <span className="verified"><ShieldCheck size={13}/> Verified</span>}</div>
      <p>{subtitle}</p>
      <div className="card-meta">{price != null && <span>₹{price}</span>}<span><CheckCircle2 size={14}/> {item?.status || 'Listed'}</span></div>
      <Button onClick={() => onAction(item)}>{type === 'doctors' ? 'Book appointment' : type === 'hotels' ? 'View rooms / book' : 'Book service'} <ArrowRight size={15}/></Button>
    </div>
  </article>
}
function AuthModal({ mode, onClose, onAuth, notify }) {
  const [tab, setTab] = useState(mode || 'login')
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '', phone: '' })
  const change = e => setForm({ ...form, [e.target.name]: e.target.value })
  async function submit(e) {
    e.preventDefault(); setBusy(true)
    try {
      const data = tab === 'signup'
        ? await api('/auth/signup', { method: 'POST', body: JSON.stringify({ name: form.name, email: form.email, password: form.password, phone: form.phone || undefined }) })
        : await api('/auth/login', { method: 'POST', body: JSON.stringify({ email: form.email, password: form.password }) })
      let token = data?.access_token || data?.token || data?.accessToken
      if (!token && tab === 'signup') {
        const login = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email: form.email, password: form.password }) })
        token = login?.access_token || login?.token || login?.accessToken
      }
      if (token) setToken(token)
      if (!token && tab === 'login') throw new Error('Login response mein token nahi mila. /auth/token endpoint/schema verify karein.')
      onAuth(data); onClose()
      notify({ type: 'success', message: tab === 'signup' ? 'Account created successfully.' : 'Welcome back!' })
    } catch (err) { notify({ type: 'error', message: err.message }) }
    finally { setBusy(false) }
  }
  return <Modal title={tab === 'login' ? 'Welcome back' : 'Create your account'} onClose={onClose}>
    <div className="auth-tabs"><button className={tab === 'login' ? 'active' : ''} onClick={() => setTab('login')}>Login</button><button className={tab === 'signup' ? 'active' : ''} onClick={() => setTab('signup')}>Create account</button></div>
    <form className="stack-form" onSubmit={submit}>
      {tab === 'signup' && <Field label="Full name" name="name" placeholder="Your name" value={form.name} onChange={change} required />}
      <Field label="Email address" name="email" type="email" placeholder="you@example.com" value={form.email} onChange={change} required />
      {tab === 'signup' && <Field label="Phone (optional)" name="phone" placeholder="+91..." value={form.phone} onChange={change} />}
      <Field label="Password" name="password" type="password" placeholder="Enter password" value={form.password} onChange={change} required minLength={6} />
      <Button type="submit" disabled={busy} block>{busy ? 'Please wait…' : tab === 'login' ? <><LogIn size={17}/> Login</> : <><UserPlus size={17}/> Create account</>}</Button>
      <p className="fine-print">By continuing, you agree to our Terms and Privacy Policy.</p>
    </form>
  </Modal>
}

function BookingModal({ item, kind, onClose, notify }) {
  const [form, setForm] = useState({ date: '', time: '10:00', guests: '1', notes: '' })
  const [busy, setBusy] = useState(false)
  const title = labelOf(item)
  async function submit(e) {
    e.preventDefault()
    if (!getToken()) { notify({ type: 'error', message: 'Booking ke liye pehle login karein.' }); return }
    setBusy(true)
    const providerId = item?.id ?? item?.provider_id
    const payload = {
      provider_id: providerId,
      service_id: item?.service_id ?? item?.id,
      booking_date: form.date,
      date: form.date,
      time: form.time,
      guests: Number(form.guests),
      notes: form.notes || undefined,
      amount: Number(item?.price || item?.consultation_fee || 0)
    }
    const path = kind === 'doctors' ? '/appointments/' : kind === 'hotels' ? '/hotel-bookings/' : '/bookings/'
    try {
      const result = await api(path, { method: 'POST', body: JSON.stringify(payload) })
      notify({ type: 'success', message: `${kind === 'doctors' ? 'Appointment' : 'Booking'} request submitted.` })
      onClose()
      if (result?.id || result?.booking_id || result?.appointment_id) {
        const id = result.id || result.booking_id || result.appointment_id
        if (window.confirm('Booking create ho gaya. Kya ab payment start karna hai?')) await startPayment({ entity_type: kind === 'doctors' ? 'appointment' : kind === 'hotels' ? 'hotel_booking' : 'booking', entity_id: id, amount: payload.amount }, notify)
      }
    } catch (err) { notify({ type: 'error', message: err.message }) }
    finally { setBusy(false) }
  }
  return <Modal title={`Book ${title}`} onClose={onClose}>
    <form className="stack-form" onSubmit={submit}>
      <div className="booking-summary"><div className="provider-avatar"><span>{title.slice(0,1)}</span></div><div><b>{title}</b><p>{item?.description || item?.category || 'ServiceHub booking'}</p></div></div>
      <Field label="Date" type="date" value={form.date} min={new Date().toISOString().slice(0,10)} onChange={e => setForm({...form, date:e.target.value})} required />
      <div className="form-row"><Field label="Time" type="time" value={form.time} onChange={e => setForm({...form, time:e.target.value})} required /><Field label="Guests / people" type="number" min="1" value={form.guests} onChange={e => setForm({...form, guests:e.target.value})} required /></div>
      <Field label="Notes (optional)" value={form.notes} onChange={e => setForm({...form, notes:e.target.value})} placeholder="Any special request" />
      <Button type="submit" disabled={busy} block>{busy ? 'Submitting…' : 'Confirm booking request'}</Button>
      <p className="fine-print">Final booking fields are validated by your backend API.</p>
    </form>
  </Modal>
}

async function startPayment(entity, notify) {
  if (!getToken()) { notify({type:'error', message:'Payment se pehle login karein.'}); return }
  const key = import.meta.env.VITE_RAZORPAY_KEY_ID
  if (!key || key.includes('REPLACE_ME')) { notify({type:'error', message:'Razorpay public Key ID .env mein configure nahi hai.'}); return }
  try {
    const order = await api('/payments/create-order', { method:'POST', body:JSON.stringify(entity) })
    const orderId = order?.order_id || order?.razorpay_order_id || order?.id
    if (!orderId) throw new Error('Backend response mein Razorpay order_id nahi mila.')
    if (!window.Razorpay) {
      await new Promise((resolve, reject) => {
        const script = document.createElement('script'); script.src='https://checkout.razorpay.com/v1/checkout.js'
        script.onload=resolve; script.onerror=()=>reject(new Error('Razorpay Checkout load nahi hua.')); document.body.appendChild(script)
      })
    }
    const checkout = new window.Razorpay({
      key, order_id: orderId, name:'ServiceHub', description:'ServiceHub booking payment',
      handler: async response => {
        try {
          await api('/payments/verify', { method:'POST', body:JSON.stringify({
            ...response, payment_id: entity.entity_id, entity_id: entity.entity_id,
            order_id: response.razorpay_order_id
          }) })
          notify({type:'success', message:'Payment verification request submitted.'})
        } catch (err) { notify({type:'error', message:`Payment verify failed: ${err.message}`}) }
      },
      theme:{color:'#087f67'}
    })
    checkout.on('payment.failed', response => notify({type:'error', message:response?.error?.description || 'Payment failed.'}))
    checkout.open()
  } catch (err) { notify({type:'error', message:err.message}) }
}

function App() {
  const [page, setPage] = useState('home')
  const [user, setUser] = useState(null)
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState('login')
  const [booking, setBooking] = useState(null)
  const [notice, setNotice] = useState(null)
  const [mobileNav, setMobileNav] = useState(false)
  const [search, setSearch] = useState('')
  const [data, setData] = useState({ providers: [], doctors: [], activity: [] })
  const [loading, setLoading] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const notify = n => { setNotice(n); window.setTimeout(() => setNotice(null), 6500) }

  useEffect(() => {
    if (!getToken()) return
    api('/auth/me').then(setUser).catch(() => { setToken(''); setUser(null) })
  }, [])
  useEffect(() => {
    let alive = true
    async function load() {
      setLoading(true)
      try {
        if (['home','services','hotels','restaurants'].includes(page)) {
          const p = await api('/providers/')
          if (alive) setData(d => ({...d, providers:asArray(p)}))
        }
        if (page === 'doctors') {
          const d = await api('/doctors/')
          if (alive) setData(old => ({...old, doctors:asArray(d)}))
        }
        if (page === 'myactivity' && getToken() && user?.id) {
          const id = user.id || user.user_id
          const results = await Promise.allSettled([
            api(`/bookings/user/${id}`), api(`/orders/user/${id}`), api(`/appointments/user/${id}`), api(`/hotel-bookings/user/${id}`)
          ])
          if (alive) setData(old => ({...old, activity:results.map((r,i)=>({name:['Service bookings','Food orders','Appointments','Hotel bookings'][i], items:r.status==='fulfilled'?asArray(r.value):[], error:r.status==='rejected'?r.reason.message:''}))}))
        }
      } catch (err) { if (alive) notify({type:'error', message:err.message}) }
      finally { if (alive) setLoading(false) }
    }
    load()
    return () => { alive = false }
  }, [page, refreshKey, user?.id])

  const providers = useMemo(() => data.providers.filter(p => JSON.stringify(p).toLowerCase().includes(search.toLowerCase())), [data.providers, search])
  const doctors = useMemo(() => data.doctors.filter(p => JSON.stringify(p).toLowerCase().includes(search.toLowerCase())), [data.doctors, search])
  const go = id => { setPage(id); setMobileNav(false); setSearch('') }
  const openAuth = mode => { setAuthMode(mode); setAuthOpen(true) }
  const actionFor = kind => item => setBooking({ item, kind })

  const pageTitle = {
    home:'Your world, one booking away', services:'Find local services', hotels:'Hotels & rooms',
    restaurants:'Discover restaurants', doctors:'Find a doctor', myactivity:'Your activity', provider:'Provider workspace'
  }[page] || 'ServiceHub'
  const pageDesc = {
    home:'Book services, stays, food and healthcare — all in one place.',
    services:'Explore service providers and request a booking.',
    hotels:'Browse providers and request a hotel room booking.',
    restaurants:'Explore restaurants, menus and food ordering.',
    doctors:'Find doctors and request an appointment.',
    myactivity:'Track your bookings, orders and appointments.',
    provider:'Manage your listing using your provider account.'
  }[page]

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav?'show':''}`}>
      <div className="brand"><div className="brand-mark"><Activity size={23}/></div><div><b>ServiceHub</b><small>BOOK • CONNECT • RELAX</small></div><button className="icon-btn sidebar-close" onClick={()=>setMobileNav(false)}><X/></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav>{navItems.map(([id,label,Icon])=><button key={id} className={`nav-link ${page===id?'selected':''}`} onClick={()=>go(id)}><Icon size={18}/><span>{label}</span>{id==='myactivity'&&<ChevronDown className="nav-end" size={15}/>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="help-card"><div className="help-icon"><MessageCircle size={18}/></div><b>Need a hand?</b><p>We’re here to help you book with confidence.</p><a href="mailto:support@servicehub.example">Contact support ↗</a></div><div className="sidebar-foot"><span className="status-dot"/> API-powered workspace <span className="version">v1.0</span></div></div>
    </aside>
    {mobileNav && <div className="mobile-overlay" onClick={()=>setMobileNav(false)}/>}
    <main className="main-area">
      <header className="topbar"><button className="icon-btn mobile-menu" onClick={()=>setMobileNav(true)}><Menu/></button><div className="breadcrumb">Workspace <span>/</span> <b>{navItems.find(x=>x[0]===page)?.[1] || 'Overview'}</b></div><div className="top-actions"><div className="api-pill"><span className="status-dot"/><span>ServiceHub API</span></div>{user ? <div className="user-menu"><div className="user-avatar">{(user.name||user.email||'U').slice(0,1).toUpperCase()}</div><div className="user-name"><b>{user.name || user.email || 'Account'}</b><small>Signed in</small></div><button className="icon-btn" title="Log out" onClick={()=>{setToken('');setUser(null);notify({type:'success',message:'Logged out.'})}}><LogOut size={17}/></button></div> : <Button variant="outline" onClick={()=>openAuth('login')}><LogIn size={16}/> Login</Button>}</div></header>
      <div className="page-wrap">
        <Notice notice={notice} clear={()=>setNotice(null)}/>
        <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> SERVICEHUB / {page.toUpperCase()}</div><h1>{pageTitle}</h1><p>{pageDesc}</p></div>{page!=='home'&&<div className="heading-actions"><div className="search-box"><Search size={17}/><input placeholder="Search listings..." value={search} onChange={e=>setSearch(e.target.value)}/></div></div>}</section>
        {page==='home' && <HomePage go={go} providers={data.providers} loading={loading} actionFor={actionFor} />}
        {page==='services' && <ListingPage items={providers} type="services" loading={loading} action={actionFor('services')} />}
        {page==='hotels' && <ListingPage items={providers} type="hotels" loading={loading} action={actionFor('hotels')} />}
        {page==='restaurants' && <RestaurantsPage items={providers} loading={loading} notify={notify} />}
        {page==='doctors' && <ListingPage items={doctors} type="doctors" loading={loading} action={actionFor('doctors')} />}
        {page==='myactivity' && <ActivityPage user={user} data={data.activity} onLogin={()=>openAuth('login')} refresh={()=>setRefreshKey(x=>x+1)} />}
        {page==='provider' && <ProviderPage notify={notify} onCreated={()=>setRefreshKey(x=>x+1)} />}
        <footer className="footer"><span>© {new Date().getFullYear()} ServiceHub</span><span>Made for easier everyday bookings <HeartPulse size={14}/></span><span><a href={`${(import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/+$/,'')}/docs`} target="_blank" rel="noreferrer">API documentation ↗</a></span></footer>
      </div>
    </main>
    {authOpen && <AuthModal mode={authMode} onClose={()=>setAuthOpen(false)} onAuth={setUser} notify={notify}/>}
    {booking && <BookingModal item={booking.item} kind={booking.kind} onClose={()=>setBooking(null)} notify={notify}/>}
  </div>
}

function HomePage({go, providers, loading, actionFor}) {
  return <>
    <section className="hero-panel"><div className="hero-copy"><div className="hero-badge"><span/> YOUR EVERYDAY, MADE EASIER</div><h2>Good things happen<br/>when it’s <em>all connected.</em></h2><p>From a comfortable stay to a trusted doctor — discover and book what you need, without the hassle.</p><div className="hero-buttons"><Button onClick={()=>go('services')}>Explore services <ArrowRight size={17}/></Button><Button variant="light" onClick={()=>go('doctors')}>Find a doctor</Button></div><div className="hero-proof"><div className="proof-avatars"><i>✓</i><i>✦</i><i>+</i></div><span><b>One simple hub</b><small>For life’s everyday needs</small></span></div></div><div className="hero-art"><div className="art-orbit orbit-one"/><div className="art-orbit orbit-two"/><div className="art-center"><Activity size={48}/></div><div className="float-card stay"><BedDouble/><span><b>Stay easy</b><small>Hotels & rooms</small></span></div><div className="float-card health"><HeartPulse/><span><b>Feel better</b><small>Doctors & care</small></span></div><div className="float-card food"><Utensils/><span><b>Eat happy</b><small>Food & dining</small></span></div><div className="art-spark spark-a">✦</div><div className="art-spark spark-b">✧</div></div></section>
    <section className="section-block"><div className="section-heading"><div><span className="eyebrow">EXPLORE YOUR OPTIONS</span><h2>What do you need today?</h2><p>Everything you need, in one helpful place.</p></div><button className="text-link" onClick={()=>go('services')}>View all services <ArrowRight size={16}/></button></div><div className="category-grid">{categories.map(({id,title,desc,icon:Icon,tone},i)=><button className="category-card" key={id} onClick={()=>go(id)}><div className={`category-icon ${tone}`}><Icon size={24}/></div><span className="category-number">0{i+1}</span><h3>{title}</h3><p>{desc}</p><div className="category-arrow"><ArrowRight size={17}/></div></button>)}</div></section>
    <section className="section-block lower-section"><div className="section-heading"><div><span className="eyebrow">READY WHEN YOU ARE</span><h2>Popular near you</h2><p>Explore provider listings from ServiceHub.</p></div><button className="text-link" onClick={()=>go('services')}>Browse directory <ArrowRight size={16}/></button></div>{loading?<div className="loading-line">Loading listings…</div>:providers.length?<div className="listing-grid">{providers.slice(0,3).map((p,i)=><DataCard key={p.id||i} item={p} type="services" onAction={actionFor('services')}/>)}</div>:<Empty title="Listings will appear here" text="Once providers are added to your backend, they’ll show up in this section."/>}</section>
    <section className="trust-strip"><div className="trust-icon"><ShieldCheck size={22}/></div><div><b>Bookings, made clearer.</b><p>Explore options and manage your requests from one place.</p></div><div className="trust-points"><span><CheckCircle2/> Simple booking</span><span><CheckCircle2/> One account</span><span><CheckCircle2/> Connected services</span></div></section>
  </>
}

function ListingPage({items,type,loading,action}) {
  const title = type==='doctors'?'doctor profiles':type==='hotels'?'providers for stays':'service providers'
  return <section className="content-panel"><div className="panel-top"><div><h2>{type==='doctors'?'Doctors directory':type==='hotels'?'Stay & hotel providers':'Service directory'}</h2><p>{items.length} listing{items.length===1?'':'s'} found</p></div><span className="panel-tag"><Activity size={14}/> Live API data</span></div>
    {loading?<div className="loading-line">Loading from backend…</div>:items.length?<div className="listing-grid">{items.map((item,i)=><DataCard key={item.id||item.provider_id||i} item={item} type={type} onAction={action}/>)}</div>:<Empty title={`No ${title} found`} text="Check that your backend has records, or try another search."/>}
  </section>
}

function RestaurantsPage({items,loading,notify}) {
  const [selected,setSelected]=useState(null)
  const [menu,setMenu]=useState([])
  const [menuLoading,setMenuLoading]=useState(false)
  async function openMenu(item) {
    const id=item?.id??item?.provider_id
    setSelected(item);setMenu([]);setMenuLoading(true)
    try {setMenu(asArray(await api(`/restaurants/${id}/menu`)))}
    catch(err){notify({type:'error',message:err.message})}
    finally{setMenuLoading(false)}
  }
  async function order(item) {
    if (!getToken()) {notify({type:'error',message:'Food order ke liye login karein.'});return}
    try {
      await api('/orders/',{method:'POST',body:JSON.stringify({provider_id:selected?.id??selected?.provider_id,items:[{menu_item_id:item.id,quantity:1}],order_type:'delivery'})})
      notify({type:'success',message:'Order request submitted.'})
    } catch(err){notify({type:'error',message:err.message})}
  }
  return <section className="content-panel"><div className="panel-top"><div><h2>Restaurants & menus</h2><p>Choose a restaurant to load its menu.</p></div></div>
    {loading?<div className="loading-line">Loading restaurants…</div>:items.length?<div className="listing-grid">{items.map((item,i)=><article className="data-card" key={item.id||i}><div className="provider-avatar restaurants"><Utensils/></div><div className="data-card-body"><h3>{labelOf(item,'Restaurant')}</h3><p>{item.address||item.description||item.category||'Restaurant listing'}</p><Button onClick={()=>openMenu(item)}>View menu <ArrowRight size={15}/></Button></div></article>)}</div>:<Empty title="No restaurants found" text="Add restaurant providers through your API to display them here."/>}
    {selected&&<div className="menu-panel"><div className="panel-top"><div><h2>{labelOf(selected)} menu</h2><p>Menu items loaded from backend</p></div><button className="icon-btn" onClick={()=>setSelected(null)}><X/></button></div>{menuLoading?<div className="loading-line">Loading menu…</div>:menu.length?<div className="menu-grid">{menu.map((item,i)=><div className="menu-item" key={item.id||i}><div><b>{labelOf(item,'Menu item')}</b><p>{item.description||'Freshly prepared'}</p><strong>₹{item.price??'—'}</strong></div><Button variant="outline" onClick={()=>order(item)}>Order</Button></div>)}</div>:<Empty title="Menu is empty" text="No menu items were returned for this restaurant." />}</div>}
  </section>
}

function ActivityPage({user,data,onLogin,refresh}) {
  if (!user) return <section className="content-panel"><Empty title="Sign in to see your activity" text="Your bookings, orders and appointments will appear here after you log in."/><div className="centered"><Button onClick={onLogin}><LogIn size={16}/> Login to continue</Button></div></section>
  return <div className="activity-stack"><div className="activity-toolbar"><div><b>Account activity</b><p>Items linked to your account</p></div><Button variant="outline" onClick={refresh}>Refresh activity</Button></div>{data.length?data.map(section=><section className="content-panel" key={section.name}><div className="panel-top"><div><h2>{section.name}</h2><p>{section.items.length} record(s)</p></div></div>{section.error?<p className="inline-error">{section.error}</p>:section.items.length?<div className="activity-list">{section.items.map((item,i)=><div className="activity-row" key={item.id||i}><div className="activity-icon"><CalendarDays/></div><div className="activity-main"><b>{labelOf(item,section.name.slice(0,-1))}</b><p>{item.date||item.booking_date||item.created_at||item.status||'Request submitted'}</p></div><span className={`state-pill ${(item.status||'pending').toLowerCase()}`}>{item.status||'Pending'}</span></div>)}</div>:<Empty title="No records yet" text="Your new requests will show up here."/>}</section>):<Empty title="Loading your activity" text="If this stays empty, confirm the logged-in user response includes an id."/>}</div>
}

function ProviderPage({notify,onCreated}) {
  const [kind,setKind]=useState('service')
  const [busy,setBusy]=useState(false)
  const [form,setForm]=useState({name:'',description:'',category:'service',price:'',address:'',provider_id:'',specialization:'',consultation_fee:'',date:'',start_time:'09:00',end_time:'17:00'})
  const change=e=>setForm({...form,[e.target.name]:e.target.value})
  async function submit(e) {
    e.preventDefault()
    if(!getToken()){notify({type:'error',message:'Provider listing ke liye login karein.'});return}
    setBusy(true)
    try {
      let path, payload
      if(kind==='provider'){path='/providers/';payload={name:form.name,description:form.description,category:form.category,address:form.address}}
      else if(kind==='service'){path=`/providers/${form.provider_id}/services`;payload={name:form.name,description:form.description,price:Number(form.price||0)}}
      else if(kind==='room'){path=`/hotels/${form.provider_id}/rooms`;payload={name:form.name,description:form.description,price:Number(form.price||0)}}
      else if(kind==='doctor'){path=`/doctors/${form.provider_id}/profile`;payload={specialization:form.specialization||form.name,consultation_fee:Number(form.consultation_fee||0),description:form.description}}
      else {path=`/doctors/${form.provider_id}/slots`;payload={date:form.date,start_time:form.start_time,end_time:form.end_time}}
      const result=await api(path,{method:'POST',body:JSON.stringify(payload)})
      notify({type:'success',message:'Request submitted successfully.'});setForm({...form,name:'',description:'',price:''});onCreated?.()
    } catch(err){notify({type:'error',message:err.message})}
    finally{setBusy(false)}
  }
  return <div className="content-panel provider-workspace"><div className="panel-top"><div><h2>Manage your business</h2><p>Create or update provider-side records through the API.</p></div><span className="panel-tag">Provider tools</span></div>
    <div className="provider-tabs">{[['provider','Create provider'],['service','Add service'],['room','Add hotel room'],['doctor','Doctor profile'],['slot','Doctor slot']].map(([id,label])=><button key={id} className={kind===id?'active':''} onClick={()=>setKind(id)}>{label}</button>)}</div>
    <form className="stack-form provider-form" onSubmit={submit}>
      {(kind==='provider'||kind==='service'||kind==='room'||kind==='doctor')&&<Field label={kind==='provider'?'Business name':kind==='doctor'?'Doctor name / specialization':kind==='room'?'Room name':'Service name'} name="name" value={form.name} onChange={change} required/>}
      {(kind==='service'||kind==='room'||kind==='doctor'||kind==='slot')&&<Field label="Provider ID" name="provider_id" value={form.provider_id} onChange={change} required placeholder="ID from provider record"/>}
      {kind==='provider'&&<><SelectField label="Category" name="category" value={form.category} onChange={change} options={[{value:'service',label:'Local service'},{value:'hotel',label:'Hotel'},{value:'restaurant',label:'Restaurant'},{value:'doctor',label:'Doctor'}]}/><Field label="Address" name="address" value={form.address} onChange={change} placeholder="Business address"/></>}
      {(kind==='provider'||kind==='service'||kind==='room'||kind==='doctor')&&<Field label="Description" name="description" value={form.description} onChange={change} placeholder="Tell customers about your listing"/>}
      {(kind==='service'||kind==='room')&&<Field label="Price (INR)" name="price" type="number" min="0" value={form.price} onChange={change}/>}
      {kind==='doctor'&&<><Field label="Specialization" name="specialization" value={form.specialization} onChange={change} placeholder="e.g. General Physician"/><Field label="Consultation fee (INR)" name="consultation_fee" type="number" min="0" value={form.consultation_fee} onChange={change}/></>}
      {kind==='slot'&&<div className="form-row"><Field label="Date" name="date" type="date" value={form.date} onChange={change} required/><Field label="Start time" name="start_time" type="time" value={form.start_time} onChange={change} required/><Field label="End time" name="end_time" type="time" value={form.end_time} onChange={change} required/></div>}
      <Button type="submit" disabled={busy}>{busy?'Submitting…':'Submit to backend'} <ArrowRight size={16}/></Button>
      <p className="fine-print">Backend authorization and exact required fields depend on your API schemas and account role.</p>
    </form>
  </div>
}

export default App