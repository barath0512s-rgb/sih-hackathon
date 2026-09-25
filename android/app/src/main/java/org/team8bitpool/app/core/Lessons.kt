package org.team8bitpool.app.core

import org.json.JSONArray
import org.json.JSONObject

/** Port of lesson_engine.grade: "green" | "yellow" | "red". */
fun gradeAnswer(acceptAnswers: JSONObject?, answer: String?): String {
    val key = TextNorm.key(answer ?: "")
    if (key.isEmpty()) return "red"
    if (acceptAnswers == null || acceptAnswers.length() == 0) return "yellow"
    if (key.all { it in '0'..'9' } && acceptAnswers.optJSONArray("digits").strings().contains(key)) return "green"
    val words = acceptAnswers.optJSONArray("hi").strings() + acceptAnswers.optJSONArray("sat").strings()
    return if (words.any { TextNorm.key(it) == key }) "green" else "yellow"
}

fun JSONArray?.strings(): List<String> =
    if (this == null) emptyList() else (0 until length()).map { optString(it) }

/** Port of lesson_engine.LessonSession (in memory; M5 syncs the analytics). */
class LessonSession(val sid: String, val grade: String, val topic: String, val lesson: JSONObject,
                    private val clock: () -> Long = System::currentTimeMillis) {
    val steps: JSONArray = lesson.getJSONArray("steps")
    val totalSteps get() = steps.length()
    var stepIdx = 0
        private set
    val translations = mutableListOf<JSONObject>()
    val responses = mutableListOf<JSONObject>()
    private val started = clock()

    val currentStep: JSONObject? get() = if (stepIdx >= totalSteps) null else steps.getJSONObject(stepIdx)

    fun advance() { stepIdx = minOf(stepIdx + 1, totalSteps) }

    fun goto(step: Int) { stepIdx = maxOf(0, minOf(step, totalSteps - 1)) }

    fun recordTranslation(hindi: String, santali: String, latencySec: Double) {
        translations += JSONObject().put("step", stepIdx).put("hindi", hindi).put("santali", santali)
            .put("latency", latencySec)
    }

    fun checkResponse(answer: String, step: Int): String {
        require(step in 0 until totalSteps) { "step $step is outside this lesson (0-${totalSteps - 1})" }
        val signal = gradeAnswer(steps.getJSONObject(step).optJSONObject("accept_answers"), answer)
        responses += JSONObject().put("step", step).put("response", answer).put("signal", signal)
        return signal
    }

    fun summary(): JSONObject {
        val elapsed = (clock() - started) / 1000
        val green = responses.count { it.getString("signal") == "green" }
        val yellow = responses.count { it.getString("signal") == "yellow" }
        val red = responses.count { it.getString("signal") == "red" }
        val total = responses.size
        val pct = if (total > 0) Math.rint(green * 100.0 / total).toInt() else 0   // Python round(): half to even
        val verdict = when {
            pct >= 70 -> "Good — students grasped the concept"
            pct >= 40 -> "Partial — repeat key terms next session"
            else -> "Needs reinforcement — revisit this lesson"
        }
        val avg = if (translations.isEmpty()) 0.0
            else Math.rint(translations.sumOf { it.getDouble("latency") } / translations.size * 100) / 100.0
        return JSONObject()
            .put("lesson_title", lesson.getString("title"))
            .put("competency", lesson.optString("competency"))
            .put("duration", "${elapsed / 60}m ${elapsed % 60}s")
            .put("steps_completed", stepIdx)
            .put("total_steps", totalSteps)
            .put("sentences_translated", translations.size)
            .put("avg_latency_sec", avg)
            .put("comprehension", JSONObject().put("green", green).put("yellow", yellow).put("red", red)
                .put("score_percent", pct).put("verdict", verdict))
    }
}
