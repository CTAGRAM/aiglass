package com.meta.wearable.dat.externalsampleapps.cameraaccess.openclaw

import org.json.JSONArray
import org.json.JSONObject

// Gemini Tool Call (parsed from server JSON)

data class GeminiFunctionCall(
    val id: String,
    val name: String,
    val args: Map<String, Any?>
)

data class GeminiToolCall(
    val functionCalls: List<GeminiFunctionCall>
) {
    companion object {
        fun fromJSON(json: JSONObject): GeminiToolCall? {
            val toolCall = json.optJSONObject("toolCall") ?: return null
            val calls = toolCall.optJSONArray("functionCalls") ?: return null
            val functionCalls = mutableListOf<GeminiFunctionCall>()
            for (i in 0 until calls.length()) {
                val call = calls.getJSONObject(i)
                val id = call.optString("id", "")
                val name = call.optString("name", "")
                if (id.isEmpty() || name.isEmpty()) continue
                val argsObj = call.optJSONObject("args")
                val args = mutableMapOf<String, Any?>()
                if (argsObj != null) {
                    for (key in argsObj.keys()) {
                        args[key] = argsObj.opt(key)
                    }
                }
                functionCalls.add(GeminiFunctionCall(id, name, args))
            }
            return if (functionCalls.isNotEmpty()) GeminiToolCall(functionCalls) else null
        }
    }
}

// Gemini Tool Call Cancellation

data class GeminiToolCallCancellation(
    val ids: List<String>
) {
    companion object {
        fun fromJSON(json: JSONObject): GeminiToolCallCancellation? {
            val cancellation = json.optJSONObject("toolCallCancellation") ?: return null
            val idsArray = cancellation.optJSONArray("ids") ?: return null
            val ids = mutableListOf<String>()
            for (i in 0 until idsArray.length()) {
                ids.add(idsArray.getString(i))
            }
            return if (ids.isNotEmpty()) GeminiToolCallCancellation(ids) else null
        }
    }
}

// Tool Result

sealed class ToolResult {
    data class Success(val result: String) : ToolResult()
    data class Failure(val error: String) : ToolResult()

    fun toJSON(): JSONObject = when (this) {
        is Success -> JSONObject().put("result", result)
        is Failure -> JSONObject().put("error", error)
    }
}

// Tool Call Status (for UI)

sealed class ToolCallStatus {
    data object Idle : ToolCallStatus()
    data class Executing(val name: String) : ToolCallStatus()
    data class Completed(val name: String) : ToolCallStatus()
    data class Failed(val name: String, val error: String) : ToolCallStatus()
    data class Cancelled(val name: String) : ToolCallStatus()

    val displayText: String
        get() = when (this) {
            is Idle -> ""
            is Executing -> "Running: $name..."
            is Completed -> "Done: $name"
            is Failed -> "Failed: $name - $error"
            is Cancelled -> "Cancelled: $name"
        }

    val isActive: Boolean
        get() = this is Executing
}

// OpenClaw Connection State

sealed class OpenClawConnectionState {
    data object NotConfigured : OpenClawConnectionState()
    data object Checking : OpenClawConnectionState()
    data object Connected : OpenClawConnectionState()
    data class Unreachable(val message: String) : OpenClawConnectionState()
}

// Tool Declarations (for Gemini setup message)

object ToolDeclarations {
    fun allDeclarationsJSON(): JSONArray {
        return JSONArray()
            .put(executeJSON())
            .put(identifyPersonJSON())
            .put(savePersonJSON())
            .put(scanPaymentQrJSON())
            .put(initiatePaymentJSON())
    }

    private fun executeJSON(): JSONObject {
        return JSONObject().apply {
            put("name", "execute")
            put("description", "Your only way to take action. You have no memory, storage, or ability to do anything on your own -- use this tool for everything: sending messages, searching the web, adding to lists, setting reminders, creating notes, research, drafts, scheduling, smart home control, app interactions, or any request that goes beyond answering a question. When in doubt, use this tool.")
            put("parameters", JSONObject().apply {
                put("type", "object")
                put("properties", JSONObject().apply {
                    put("task", JSONObject().apply {
                        put("type", "string")
                        put("description", "Clear, detailed description of what to do. Include all relevant context: names, content, platforms, quantities, etc.")
                    })
                })
                put("required", JSONArray().put("task"))
            })
            put("behavior", "BLOCKING")
        }
    }

    private fun identifyPersonJSON(): JSONObject {
        return JSONObject().apply {
            put("name", "identify_person")
            put("description", "Recognize the person currently in view, but ONLY among people the user has saved. Call this when the user asks who someone is ('who is this?', 'do I know them?'). Returns their name, the user's notes, what they last talked about and their linked public profile. If they aren't saved, say you don't recognize them. Never guess a stranger's identity.")
            put("parameters", JSONObject().apply {
                put("type", "object")
                put("properties", JSONObject())
            })
            put("behavior", "BLOCKING")
        }
    }

    private fun savePersonJSON(): JSONObject {
        return JSONObject().apply {
            put("name", "save_person")
            put("description", "Save the person currently in view so they can be recognized later. Call when the user asks to remember someone ('save this as Alice', 'remember him as my coworker Bob'). Only save people who have agreed to it.")
            put("parameters", JSONObject().apply {
                put("type", "object")
                put("properties", JSONObject().apply {
                    put("name", JSONObject().apply {
                        put("type", "string")
                        put("description", "The person's name")
                    })
                    put("notes", JSONObject().apply {
                        put("type", "string")
                        put("description", "Optional note about them, e.g. 'colleague from work'")
                    })
                    put("profile", JSONObject().apply {
                        put("type", "string")
                        put("description", "Optional public profile they shared with the user, e.g. a GitHub or LinkedIn URL or handle")
                    })
                })
                put("required", JSONArray().put("name"))
            })
            put("behavior", "BLOCKING")
        }
    }

    private fun scanPaymentQrJSON(): JSONObject {
        return JSONObject().apply {
            put("name", "scan_payment_qr")
            put("description", "Scan the UPI payment QR code the user is looking at through the glasses camera. Call when the user wants to pay a QR ('pay this', 'scan this QR', 'pay here'). Returns the payee name and whether the amount is fixed. After scanning, tell the user the payee name and ask how much to pay if the amount is open.")
            put("parameters", JSONObject().apply {
                put("type", "object")
                put("properties", JSONObject())
            })
            put("behavior", "BLOCKING")
        }
    }

    private fun initiatePaymentJSON(): JSONObject {
        return JSONObject().apply {
            put("name", "initiate_payment")
            put("description", "Open the phone's UPI app pre-filled with the scanned payee and the given amount. ONLY call this AFTER the user has explicitly confirmed BOTH the payee name and the exact amount out loud. The user completes and authorizes the payment on their phone; this only prepares it.")
            put("parameters", JSONObject().apply {
                put("type", "object")
                put("properties", JSONObject().apply {
                    put("amount", JSONObject().apply {
                        put("type", "string")
                        put("description", "Amount in Indian rupees as a plain number, e.g. '250' or '99.50'")
                    })
                })
                put("required", JSONArray().put("amount"))
            })
            put("behavior", "BLOCKING")
        }
    }
}
