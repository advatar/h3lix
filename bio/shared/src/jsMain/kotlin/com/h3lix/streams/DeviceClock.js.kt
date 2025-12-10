package com.h3lix.streams

import kotlin.js.Date

actual fun deviceUptimeSeconds(): Double = Date().getTime() / 1000.0
