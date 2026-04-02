package com.escuelaing.cvsagent.sensors

import android.app.usage.UsageStatsManager
import android.content.Context

class ScreenTimeCollector(private val context: Context) {
    fun getScreenTimeMinutesLastHour(): Float {
        val manager = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val end = System.currentTimeMillis()
        val start = end - 60L * 60L * 1000L
        val stats = manager.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, start, end)
        val totalForegroundMs = stats.sumOf { it.totalTimeInForeground }
        return totalForegroundMs / 60000f
    }
}
