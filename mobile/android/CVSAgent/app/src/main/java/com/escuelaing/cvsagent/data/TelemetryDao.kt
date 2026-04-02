package com.escuelaing.cvsagent.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface TelemetryDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(readings: List<SensorReading>)

    @Query("SELECT * FROM sensor_readings ORDER BY sampledAt ASC LIMIT :limit")
    suspend fun getPending(limit: Int = 200): List<SensorReading>

    @Query("DELETE FROM sensor_readings WHERE id IN (:ids)")
    suspend fun deleteByIds(ids: List<Long>)
}
