package nl.jarvis.mobile.domain

enum class NotificationCategory { urgent, appointments, important, news }
enum class CallState { unavailable, ringing, accepted, declined, ended }
data class FutureCall(val id: String, val category: NotificationCategory, val state: CallState) {
    fun canRingAutomatically() = category == NotificationCategory.urgent
}
interface FutureCallTransport {
    suspend fun accept(id: String)
    suspend fun decline(id: String)
    suspend fun end(id: String)
}
// No transport implementation, Telecom registration, STUN/TURN or working call button in phase 6.
