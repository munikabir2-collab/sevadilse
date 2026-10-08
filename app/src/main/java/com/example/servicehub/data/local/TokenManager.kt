package com.example.servicehub.data.local

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.authDataStore by preferencesDataStore(
    name = "servicehub_auth"
)

class TokenManager(
    private val context: Context
) {

    companion object {
        private val ACCESS_TOKEN =
            stringPreferencesKey("access_token")

        private val USER_ID =
            intPreferencesKey("user_id")

        private val PROVIDER_ID =
            intPreferencesKey("provider_id")

        private val IS_PROVIDER =
            booleanPreferencesKey("is_provider")

        private val IS_ADMIN =
            booleanPreferencesKey("is_admin")
    }

    val token: Flow<String?> =
        context.authDataStore.data.map { preferences ->
            preferences[ACCESS_TOKEN]
        }

    val userId: Flow<Int?> =
        context.authDataStore.data.map { preferences ->
            preferences[USER_ID]
        }

    val providerId: Flow<Int?> =
        context.authDataStore.data.map { preferences ->
            preferences[PROVIDER_ID]
        }

    val isProvider: Flow<Boolean> =
        context.authDataStore.data.map { preferences ->
            preferences[IS_PROVIDER] ?: false
        }

    val isAdmin: Flow<Boolean> =
        context.authDataStore.data.map { preferences ->
            preferences[IS_ADMIN] ?: false
        }

    suspend fun saveToken(
        accessToken: String,
        userId: Int,
        providerId: Int?,
        isProvider: Boolean,
        isAdmin: Boolean
    ) {
        context.authDataStore.edit { preferences ->

            preferences[ACCESS_TOKEN] = accessToken
            preferences[USER_ID] = userId

            if (providerId != null) {
                preferences[PROVIDER_ID] = providerId
            } else {
                preferences.remove(PROVIDER_ID)
            }

            preferences[IS_PROVIDER] = isProvider
            preferences[IS_ADMIN] = isAdmin
        }
    }

    suspend fun clear() {
        context.authDataStore.edit { preferences ->
            preferences.clear()
        }
    }
}