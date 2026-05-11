package com.youtube.converter

import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

object PythonManager {

    @Volatile
    private var initialized = false

    fun init(context: Context) {
        if (!initialized) {
            synchronized(this) {
                if (!initialized) {
                    if (!Python.isStarted()) {
                        Python.start(AndroidPlatform(context))
                    }
                    initialized = true
                }
            }
        }
    }

    fun getConverter() = Python.getInstance().getModule("converter")
}
