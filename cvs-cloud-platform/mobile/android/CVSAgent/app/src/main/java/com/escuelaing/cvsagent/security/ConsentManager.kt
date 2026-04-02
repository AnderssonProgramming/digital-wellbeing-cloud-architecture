package com.escuelaing.cvsagent.security

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.security.MessageDigest
import java.util.UUID

/**
 * Manages user consent state and device UUID lifecycle.
 *
 * Consent is stored in EncryptedSharedPreferences.
 * consent_hash = SHA-256(consentDocumentVersion + "|" + consentTimestampMillis)
 * This hash is included in every TelemetryBatch for GDPR Article 7 audit trail.
 */
class ConsentManager(context: Context) {

    companion object {
        private const val PREFS_FILE = "cvs_consent_prefs"
        private const val KEY_DEVICE_UUID = "device_uuid"
        private const val KEY_CONSENT_HASH = "consent_hash"
        private const val KEY_CONSENT_GIVEN = "consent_given"
        const val CONSENT_DOC_VERSION = "v1.0.0"
    }

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs = EncryptedSharedPreferences.create(
        context, PREFS_FILE, masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    val hasConsent: Boolean get() = prefs.getBoolean(KEY_CONSENT_GIVEN, false)

    val deviceUuid: String
        get() = prefs.getString(KEY_DEVICE_UUID, null)
            ?: error("Device UUID not initialized. Call grantConsent() first.")

    val consentHash: String
        get() = prefs.getString(KEY_CONSENT_HASH, null)
            ?: error("Consent hash not set.")

    fun grantConsent() {
        val newUuid = UUID.randomUUID().toString()
        val timestamp = System.currentTimeMillis()
        val rawInput = "$CONSENT_DOC_VERSION|$timestamp"
        val hash = sha256(rawInput)

        prefs.edit()
            .putString(KEY_DEVICE_UUID, newUuid)
            .putString(KEY_CONSENT_HASH, hash)
            .putBoolean(KEY_CONSENT_GIVEN, true)
            .apply()
    }

    fun revokeConsent() {
        prefs.edit().clear().apply()
    }

    private fun sha256(input: String): String {
        val bytes = MessageDigest.getInstance("SHA-256").digest(input.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
