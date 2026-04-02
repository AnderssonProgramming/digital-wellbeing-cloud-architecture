package com.escuelaing.cvsagent.sensors

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager

/**
 * Collects ambient light readings from the device ALS sensor.
 * Returns null if the sensor is unavailable or returns a negative value.
 *
 * Clinical reference: Blehm et al. (2005). Illuminance mismatch is a primary CVS trigger.
 */
class AmbientLightCollector(context: Context) : SensorEventListener {

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val sensor: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_LIGHT)

    @Volatile
    private var lastValueLux: Float? = null

    fun startListening() {
        sensor?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_NORMAL)
        }
    }

    fun stopListening() {
        sensorManager.unregisterListener(this)
    }

    /** Returns last valid lux reading, or null if unavailable or sensor not present. */
    fun getLastReading(): Float? = lastValueLux?.takeIf { it >= 0f }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type == Sensor.TYPE_LIGHT) {
            lastValueLux = event.values[0]
        }
    }

    override fun onAccuracyChanged(sensor: Sensor, accuracy: Int) = Unit
}
