package com.escuelaing.cvsagent.mqtt

import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttMessage

class MqttPublisher(
    brokerUrl: String,
    clientId: String,
) {
    private val client = MqttClient(brokerUrl, clientId)

    fun connect(username: String? = null, password: String? = null) {
        val options = MqttConnectOptions().apply {
            isAutomaticReconnect = true
            isCleanSession = true
            connectionTimeout = 10
            keepAliveInterval = 30
            userName = username
            if (password != null) {
                this.password = password.toCharArray()
            }
        }
        if (!client.isConnected) {
            client.connect(options)
        }
    }

    fun publish(topic: String, payload: String, qos: Int = 1) {
        val message = MqttMessage(payload.toByteArray()).apply {
            this.qos = qos
        }
        client.publish(topic, message)
    }

    fun disconnect() {
        if (client.isConnected) {
            client.disconnect()
        }
    }
}
