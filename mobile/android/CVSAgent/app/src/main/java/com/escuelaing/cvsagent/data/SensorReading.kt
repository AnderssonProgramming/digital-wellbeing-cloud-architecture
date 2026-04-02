package com.escuelaing.cvsagent.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "sensor_readings")
data class SensorReading(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val deviceUuid: String,
    val sensorType: String,
    val value: Float,
    val unit: String,
    val sampledAt: Long,
    val batchTimestamp: Long,
    val consentHash: String,
)
