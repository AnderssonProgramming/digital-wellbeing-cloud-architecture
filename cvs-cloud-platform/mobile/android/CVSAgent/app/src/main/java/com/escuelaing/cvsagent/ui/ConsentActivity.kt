package com.escuelaing.cvsagent.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.escuelaing.cvsagent.security.ConsentManager

class ConsentActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val consentManager = ConsentManager(this)
        if (consentManager.hasConsent) {
            startActivity(Intent(this, StatusActivity::class.java))
            finish()
            return
        }

        val title = TextView(this).apply {
            text = "CVS Agent Consent"
            textSize = 20f
            setPadding(32, 64, 32, 32)
        }

        val message = TextView(this).apply {
            text = "This app collects ambient light, proximity, and screen-time data for CVS risk analytics."
            setPadding(32, 0, 32, 32)
        }

        val allowButton = Button(this).apply {
            text = "I Agree"
            setOnClickListener {
                consentManager.grantConsent()
                startActivity(Intent(this@ConsentActivity, StatusActivity::class.java))
                finish()
            }
        }

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(title)
            addView(message)
            addView(allowButton)
        }

        setContentView(root)
    }
}
