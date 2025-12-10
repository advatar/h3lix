package com.h3lix.streams

import platform.Foundation.NSProcessInfo

actual fun deviceUptimeSeconds(): Double = NSProcessInfo.processInfo.systemUptime
