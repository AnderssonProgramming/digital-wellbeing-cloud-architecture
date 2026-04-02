package com.escuelaing.cvsagent.workers

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.escuelaing.cvsagent.data.SensorReading
import com.escuelaing.cvsagent.data.TelemetryDatabase
import com.escuelaing.cvsagent.security.ConsentManager
import com.escuelaing.cvsagent.sensors.AmbientLightCollector
import com.escuelaing.cvsagent.sensors.ProximitySensorCollector
import com.escuelaing.cvsagent.sensors.ScreenTimeCollector

class SensorSamplingWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val consent = ConsentManager(applicationContext)
        if (!consent.hasConsent) {
            return Result.success()
        }

        val now = System.currentTimeMillis()
        val ambient = AmbientLightCollector(applicationContext)
        val proximity = ProximitySensorCollector(applicationContext)
        val screen = ScreenTimeCollector(applicationContext)

        ambient.startListening()
        proximity.startListening()

        val readings = listOf(
            SensorReading(
                deviceUuid = consent.deviceUuid,
                sensorType = "AMBIENT_LIGHT",
                value = ambient.getLastReading() ?: -1f,
                unit = "lux",
                sampledAt = now,
                batchTimestamp = now,
                consentHash = consent.consentHash,
            ),
            SensorReading(
                deviceUuid = consent.deviceUuid,
                sensorType = "PROXIMITY",
                value = proximity.getLastReading() ?: -1f,
                unit = "cm",
                sampledAt = now,
                batchTimestamp = now,
                consentHash = consent.consentHash,
            ),
            SensorReading(
                deviceUuid = consent.deviceUuid,
                sensorType = "SCREEN_TIME",
                value = screen.getScreenTimeMinutesLastHour(),
                unit = "min",
                sampledAt = now,
                batchTimestamp = now,
                consentHash = consent.consentHash,
            ),
        )

        ambient.stopListening()
        proximity.stopListening()

        TelemetryDatabase.getInstance(applicationContext).telemetryDao().insertAll(readings)
        return Result.success()
    }
}
