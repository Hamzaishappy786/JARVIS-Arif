package com.arif.jarvis

import android.content.Context
import android.graphics.*
import android.util.AttributeSet
import android.view.View
import kotlin.math.*
import kotlin.random.Random

class WaveformView @JvmOverloads constructor(
    context: Context, attrs: AttributeSet? = null
) : View(context, attrs) {

    private val BAR_COUNT = 80
    private val bars    = FloatArray(BAR_COUNT)
    private val targets = FloatArray(BAR_COUNT)
    private val phases  = FloatArray(BAR_COUNT) { Random.nextFloat() * PI.toFloat() * 2f }

    private var amplitude = 0f
    private var isActive  = false
    private var tick      = 0f

    // Adapted bar colors — set via adaptToBackground()
    private var colorLow  = Color.parseColor("#002233")
    private var colorMid  = Color.parseColor("#0099CC")
    private var colorHigh = Color.parseColor("#00D4FF")
    private var colorPeak = Color.parseColor("#AAEEFF")

    private val barPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style   = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
    }
    private val glowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style       = Paint.Style.STROKE
        strokeCap   = Paint.Cap.ROUND
        maskFilter  = BlurMaskFilter(14f, BlurMaskFilter.Blur.NORMAL)
    }
    private val ringPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
    }
    private val ringGlowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style      = Paint.Style.STROKE
        maskFilter = BlurMaskFilter(18f, BlurMaskFilter.Blur.NORMAL)
    }

    // ── Public API ────────────────────────────────────────────────────────────

    fun setAmplitude(amp: Float) { amplitude = amp.coerceIn(0f, 1f) }
    fun startActive() { isActive = true; invalidate() }
    fun stopActive()  { isActive = false; amplitude = 0f }

    /** Call whenever the background color changes so bars contrast nicely. */
    fun adaptToBackground(bgColor: Int) {
        val r = Color.red(bgColor)   / 255f
        val g = Color.green(bgColor) / 255f
        val b = Color.blue(bgColor)  / 255f
        val luminance  = 0.299f * r + 0.587f * g + 0.114f * b

        val hsv = FloatArray(3)
        Color.colorToHSV(bgColor, hsv)
        val saturation = hsv[1]

        if (luminance < 0.35f && saturation < 0.25f) {
            // Dark neutral → default cyan neon
            colorLow  = Color.parseColor("#002233")
            colorMid  = Color.parseColor("#0099CC")
            colorHigh = Color.parseColor("#00D4FF")
            colorPeak = Color.parseColor("#AAEEFF")
        } else {
            // Derive complementary hue for maximum contrast
            val compHue  = (hsv[0] + 180f) % 360f
            val brightness = if (luminance < 0.45f) 1.0f else 0.75f
            val sat        = if (luminance > 0.65f) 1.0f else 0.9f
            colorLow  = Color.HSVToColor(floatArrayOf(compHue, sat * 0.35f, brightness * 0.35f))
            colorMid  = Color.HSVToColor(floatArrayOf(compHue, sat * 0.75f, brightness * 0.70f))
            colorHigh = Color.HSVToColor(floatArrayOf(compHue, sat,          brightness))
            colorPeak = Color.HSVToColor(floatArrayOf(compHue, sat * 0.25f,  1.0f))
        }
        invalidate()
    }

    // ── Drawing ───────────────────────────────────────────────────────────────

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        tick += 0.05f

        val cx    = width  / 2f
        val cy    = height / 2f
        val size  = minOf(width, height).toFloat()
        val innerR = size * 0.28f   // radius of the ring bars start from
        val maxBar = size * 0.24f   // max bar length outward (taller when active)

        // ── Pulsing inner ring ──────────────────────────────────────────────
        val pulseT = if (isActive) 0.5f + amplitude * 0.5f
                     else 0.5f + sin(tick.toDouble()).toFloat() * 0.12f + 0.12f

        ringGlowPaint.color       = colorHigh
        ringGlowPaint.alpha       = (50 + pulseT * 80).toInt()
        ringGlowPaint.strokeWidth = 10f
        canvas.drawCircle(cx, cy, innerR, ringGlowPaint)

        ringPaint.color       = colorHigh
        ringPaint.alpha       = (90 + pulseT * 90).toInt()
        ringPaint.strokeWidth = 2f
        canvas.drawCircle(cx, cy, innerR, ringPaint)

        // Outer boundary ring (very faint)
        ringPaint.alpha       = 20
        ringPaint.strokeWidth = 1f
        canvas.drawCircle(cx, cy, innerR + maxBar * 1.06f, ringPaint)

        // ── Radial bars ─────────────────────────────────────────────────────
        val strokeW = size * 0.011f
        for (i in 0 until BAR_COUNT) {
            val angle  = (i.toFloat() / BAR_COUNT) * 2f * PI.toFloat() - PI.toFloat() / 2f
            val cosA   = cos(angle).toFloat()
            val sinA   = sin(angle).toFloat()

            // Compute target height
            val idle = (sin(tick + phases[i]).toFloat() * 0.5f + 0.5f) * 0.10f
            targets[i] = if (isActive) {
                val noise = sin(tick * 2.1f + phases[i] * 1.9f).toFloat() * 0.5f + 0.5f
                // Boost: raise the floor and amplify peaks so waves look energetic
                val boosted = (amplitude * 2.2f).coerceIn(0f, 1f)
                (boosted * noise * 0.75f + boosted * 0.25f).coerceIn(0.08f, 1f)
            } else idle

            val speed = if (targets[i] > bars[i]) 0.30f else 0.09f
            bars[i] += (targets[i] - bars[i]) * speed

            val barLen = bars[i] * maxBar
            val ix = cx + innerR * cosA
            val iy = cy + innerR * sinA
            val ox = cx + (innerR + barLen) * cosA
            val oy = cy + (innerR + barLen) * sinA

            val t = bars[i]
            val color = when {
                t > 0.85f -> lerpColor(colorHigh, colorPeak, (t - 0.85f) / 0.15f)
                t > 0.45f -> lerpColor(colorMid,  colorHigh, (t - 0.45f) / 0.40f)
                else      -> lerpColor(colorLow,  colorMid,   t / 0.45f)
            }

            // Glow — brighter when active
            val glowBoost = if (isActive) 1.8f else 1f
            glowPaint.color       = color
            glowPaint.alpha       = (bars[i] * 180 * glowBoost).toInt().coerceIn(0, 200)
            glowPaint.strokeWidth = strokeW * (if (isActive) 4.0f else 2.8f)
            canvas.drawLine(ix, iy, ox, oy, glowPaint)

            // Bar
            barPaint.color       = color
            barPaint.strokeWidth = strokeW
            canvas.drawLine(ix, iy, ox, oy, barPaint)
        }

        postInvalidateOnAnimation()
    }

    private fun lerpColor(from: Int, to: Int, t: Float): Int {
        val r = (Color.red(from)   + (Color.red(to)   - Color.red(from))   * t).toInt()
        val g = (Color.green(from) + (Color.green(to) - Color.green(from)) * t).toInt()
        val b = (Color.blue(from)  + (Color.blue(to)  - Color.blue(from))  * t).toInt()
        return Color.rgb(r.coerceIn(0,255), g.coerceIn(0,255), b.coerceIn(0,255))
    }
}
