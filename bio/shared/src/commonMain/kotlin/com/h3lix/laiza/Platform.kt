package com.h3lix.laiza

interface Platform {
    val name: String
}

expect fun getPlatform(): Platform