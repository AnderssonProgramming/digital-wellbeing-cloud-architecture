package com.escuelaing.cvsagent.workers

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.escuelaing.cvsagent.data.TelemetryDatabase
import com.escuelaing.cvsagent.mqtt.MqttPublisher
import org.json.JSONArray
import org.json.JSONObject

class BatchPublishWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val dao = TelemetryDatabase.getInstance(applicationContext).telemetryDao()
        val batch = dao.getPending(limit = 200)
        if (batch.isEmpty()) {
            return Result.success()
        }

        val payload = JSONObject().apply {
            put("device_uuid", batch.first().deviceUuid)
            put("batch_timestamp", System.currentTimeMillis())
            put("app_version", "1.0.0")
            put("consent_hash", batch.first().consentHash)
            put("readings", JSONArray(batch.map {
                JSONObject()
                    .put("sensor_type", it.sensorType)
                    .put("value", it.value)
                    .put("unit", it.unit)
                    .put("sampled_at", it.sampledAt)
            }))
        }

        val publisher = MqttPublisher("tcp://broker:1883", "cvs-agent-publisher")
        publisher.connect()
        publisher.publish("cvs.telemetry.raw", payload.toString())
        publisher.disconnect()

        dao.deleteByIds(batch.map { it.id })
        return Result.success()
    }
}
