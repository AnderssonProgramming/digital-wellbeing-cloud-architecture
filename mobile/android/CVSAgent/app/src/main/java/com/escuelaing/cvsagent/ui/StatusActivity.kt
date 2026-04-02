package com.escuelaing.cvsagent.ui

import android.os.Bundle
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.escuelaing.cvsagent.security.ConsentManager

class StatusActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val consent = ConsentManager(this)
        val statusText = TextView(this).apply {
            text = if (consent.hasConsent) {
                "Consent active. Device UUID initialized."
            } else {
                "Consent not granted."
            }
            textSize = 18f
            setPadding(32, 64, 32, 32)
        }

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(statusText)
        }
        setContentView(root)
    }
}
