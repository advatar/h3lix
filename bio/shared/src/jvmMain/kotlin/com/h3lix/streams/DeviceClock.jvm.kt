package com.h3lix.streams

actual fun deviceUptimeSeconds(): Double = System.nanoTime() / 1_000_000_000.0
