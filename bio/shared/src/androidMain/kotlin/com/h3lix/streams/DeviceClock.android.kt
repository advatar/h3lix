package com.h3lix.streams

import android.os.SystemClock

actual fun deviceUptimeSeconds(): Double = SystemClock.elapsedRealtime() / 1000.0
