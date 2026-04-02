package com.escuelaing.cvsagent.security

import net.sqlcipher.database.SQLiteDatabase

object SQLCipherHelper {
    fun initialize(passphrase: ByteArray) {
        SQLiteDatabase.loadLibs(null)
        passphrase.fill(0)
    }
}
