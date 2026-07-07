package com.arif.jarvis

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.widget.EditText
import com.google.android.material.button.MaterialButton
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.net.Socket
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.sqrt

class MainActivity : AppCompatActivity() {

    companion object {
        private const val SAMPLE_RATE  = 16000
        private const val CHANNELS     = AudioFormat.CHANNEL_IN_MONO
        private const val ENCODING     = AudioFormat.ENCODING_PCM_16BIT
        private const val REQUEST_MIC  = 101
        private const val PREFS_NAME   = "arif_prefs"
        private const val PREF_BG_TYPE  = "bg_type"
        private const val PREF_BG_COLOR = "bg_color"
        private const val PREF_BG_URI   = "bg_uri"
    }

    private var socket: Socket? = null
    private var connected   = false
    private var isRecording = false
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private lateinit var rootLayout:    FrameLayout
    private lateinit var bgImage:       ImageView
    private lateinit var bgOverlay:     View
    private lateinit var etIp:          EditText
    private lateinit var etPort:        EditText
    private lateinit var btnConnect:    MaterialButton
    private lateinit var btnTalk:       android.widget.Button
    private lateinit var btnBackground: MaterialButton
    private lateinit var tvStatus:      TextView
    private lateinit var tvHeard:       TextView
    private lateinit var tvReply:       TextView
    private lateinit var waveform:      WaveformView

    private val pickImage = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { applyImageBackground(it, persist = true) }
    }

    private val presets: List<Pair<String, Int>> = listOf(
        "Space Black"   to Color.parseColor("#0A0F1E"),
        "Deep Purple"   to Color.parseColor("#1A0A2E"),
        "Dark Forest"   to Color.parseColor("#0A1E0F"),
        "Crimson Night" to Color.parseColor("#1E0A0A"),
        "Midnight Navy" to Color.parseColor("#070A1A"),
        "Dark Teal"     to Color.parseColor("#071A1A"),
        "Charcoal"      to Color.parseColor("#111111"),
        "Warm Night"    to Color.parseColor("#1A150A")
    )

    @SuppressLint("ClickableViewAccessibility")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        rootLayout    = findViewById(R.id.rootLayout)
        bgImage       = findViewById(R.id.bgImage)
        bgOverlay     = findViewById(R.id.bgOverlay)
        etIp          = findViewById(R.id.etIp)
        etPort        = findViewById(R.id.etPort)
        btnConnect    = findViewById(R.id.btnConnect)
        btnTalk       = findViewById(R.id.btnTalk)
        btnBackground = findViewById(R.id.btnBackground)
        tvStatus      = findViewById(R.id.tvStatus)
        tvHeard       = findViewById(R.id.tvHeard)
        tvReply       = findViewById(R.id.tvReply)
        waveform      = findViewById(R.id.waveform)

        requestMicPermission()
        restoreBackground()

        btnConnect.setOnClickListener { if (connected) disconnect() else connect() }
        btnBackground.setOnClickListener { showBackgroundPicker() }

        btnTalk.setOnTouchListener { v, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    v.animate().scaleX(1.35f).scaleY(1.35f).setDuration(120).start()
                    if (connected && !isRecording) startRecording()
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    v.animate().scaleX(1f).scaleY(1f).setDuration(150).start()
                    if (isRecording) stopRecordingAndSend()
                    true
                }
                else -> false
            }
        }
    }

    // ── Background picker ─────────────────────────────────────────────────────

    private fun showBackgroundPicker() {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_bg_picker, null)

        val dialog = AlertDialog.Builder(this, R.style.DarkDialog)
            .setView(dialogView)
            .setNegativeButton("Cancel") { d, _ -> d.dismiss() }
            .create()

        dialog.window?.setBackgroundDrawable(ColorDrawable(Color.parseColor("#0D1B2E")))

        dialogView.findViewById<MaterialButton>(R.id.btnGallery).setOnClickListener {
            dialog.dismiss()
            pickImage.launch("image/*")
        }

        val swatchIds: List<Int> = listOf(
            R.id.swatch0, R.id.swatch1, R.id.swatch2, R.id.swatch3,
            R.id.swatch4, R.id.swatch5, R.id.swatch6, R.id.swatch7
        )

        swatchIds.forEachIndexed { index: Int, viewId: Int ->
            val swatch: View = dialogView.findViewById(viewId)
            val color: Int = presets[index].second
            swatch.setBackgroundColor(color)
            swatch.outlineProvider = android.view.ViewOutlineProvider.BACKGROUND
            swatch.clipToOutline   = true
            swatch.setOnClickListener {
                applyColorBackground(color, persist = true)
                dialog.dismiss()
            }
        }

        dialog.show()
    }

    private fun applyColorBackground(color: Int, persist: Boolean) {
        bgImage.visibility   = View.GONE
        bgOverlay.visibility = View.GONE
        rootLayout.setBackgroundColor(color)
        waveform.adaptToBackground(color)
        if (persist) {
            getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit()
                .putString(PREF_BG_TYPE, "color")
                .putInt(PREF_BG_COLOR, color)
                .apply()
        }
    }

    private fun applyImageBackground(uri: Uri, persist: Boolean) {
        try {
            contentResolver.takePersistableUriPermission(
                uri, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
            )
        } catch (e: Exception) {
            // Permission may already be held or not grantable — safe to ignore
        }

        bgImage.setImageURI(uri)
        bgImage.visibility   = View.VISIBLE
        bgOverlay.visibility = View.VISIBLE
        waveform.adaptToBackground(sampleDominantColor(uri))

        if (persist) {
            getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE).edit()
                .putString(PREF_BG_TYPE, "image")
                .putString(PREF_BG_URI,  uri.toString())
                .apply()
        }
    }

    private fun restoreBackground() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        when (prefs.getString(PREF_BG_TYPE, "color")) {
            "color" -> applyColorBackground(
                prefs.getInt(PREF_BG_COLOR, Color.parseColor("#0A0F1E")),
                persist = false
            )
            "image" -> {
                val uriStr = prefs.getString(PREF_BG_URI, null)
                if (!uriStr.isNullOrEmpty()) {
                    runCatching { applyImageBackground(Uri.parse(uriStr), persist = false) }
                }
            }
        }
    }

    private fun sampleDominantColor(uri: Uri): Int {
        return try {
            val opts = BitmapFactory.Options().also { it.inSampleSize = 8 }
            val bmp  = contentResolver.openInputStream(uri)?.use { stream ->
                BitmapFactory.decodeStream(stream, null, opts)
            } ?: return Color.parseColor("#0A0F1E")
            val scaled = Bitmap.createScaledBitmap(bmp, 24, 24, true)
            var r = 0L; var g = 0L; var b = 0L
            for (x in 0 until 24) {
                for (y in 0 until 24) {
                    val pixel = scaled.getPixel(x, y)
                    r += Color.red(pixel)
                    g += Color.green(pixel)
                    b += Color.blue(pixel)
                }
            }
            val total = 576L
            Color.rgb((r / total).toInt(), (g / total).toInt(), (b / total).toInt())
        } catch (e: Exception) {
            Color.parseColor("#0A0F1E")
        }
    }

    // ── Connection ────────────────────────────────────────────────────────────

    @SuppressLint("SetTextI18n")
    private fun connect() {
        val ip   = etIp.text.toString().trim()
        val port = etPort.text.toString().trim().toIntOrNull() ?: 5050
        if (ip.isEmpty()) { setStatus("● Enter PC IP first", "#FF4444"); return }

        setStatus("● CONNECTING…", "#FFAA00")
        scope.launch(Dispatchers.IO) {
            try {
                socket = Socket(ip, port).also {
                    it.soTimeout  = 30_000
                    it.tcpNoDelay = true
                }
                withContext(Dispatchers.Main) {
                    connected = true
                    btnConnect.text = "DISCONNECT"
                    setStatus("● CONNECTED  $ip:$port  —  HOLD TO TALK", "#00FF88")
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    setStatus("● FAILED: ${e.message}", "#FF4444")
                }
            }
        }
    }

    @SuppressLint("SetTextI18n")
    private fun disconnect() {
        scope.launch(Dispatchers.IO) { runCatching { socket?.close() } }
        socket    = null
        connected = false
        btnConnect.text = "CONNECT"
        setStatus("● OFFLINE", "#FF4444")
        waveform.stopActive()
        btnTalk.background = ContextCompat.getDrawable(this, R.drawable.mic_btn_idle)
    }

    // ── Recording ─────────────────────────────────────────────────────────────

    private var audioRecord: AudioRecord? = null
    private val pcmBuffer = ByteArrayOutputStream()

    private fun startRecording() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) return

        val minBuf = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNELS, ENCODING)
        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC, SAMPLE_RATE, CHANNELS, ENCODING, minBuf * 4
        )
        pcmBuffer.reset()
        isRecording = true
        setStatus("● RECORDING…", "#FF4444")
        btnTalk.background = ContextCompat.getDrawable(this, R.drawable.mic_btn_recording)
        waveform.startActive()
        audioRecord?.startRecording()

        scope.launch(Dispatchers.IO) {
            val buf = ByteArray(minBuf)
            while (isRecording) {
                val read = audioRecord?.read(buf, 0, buf.size) ?: 0
                if (read > 0) {
                    synchronized(pcmBuffer) { pcmBuffer.write(buf, 0, read) }
                    val amp = rmsAmplitude(buf, read)
                    withContext(Dispatchers.Main) { waveform.setAmplitude(amp) }
                }
            }
        }
    }

    private fun stopRecordingAndSend() {
        isRecording = false
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null
        waveform.stopActive()
        btnTalk.background = ContextCompat.getDrawable(this, R.drawable.mic_btn_idle)

        val pcm = synchronized(pcmBuffer) { pcmBuffer.toByteArray() }
        if (pcm.isEmpty()) return

        setStatus("● PROCESSING…", "#FFAA00")

        scope.launch(Dispatchers.IO) {
            try {
                val wav  = buildWav(pcm)
                val sock = socket ?: throw IllegalStateException("Not connected")
                val out  = DataOutputStream(sock.getOutputStream())
                out.writeInt(wav.size)
                out.write(wav)
                out.flush()

                val inStream   = sock.getInputStream()
                val lenBuf     = ByteArray(4)
                inStream.read(lenBuf)
                val respLen    = ByteBuffer.wrap(lenBuf).order(ByteOrder.BIG_ENDIAN).int
                val respBuf    = ByteArray(respLen)
                var totalRead  = 0
                while (totalRead < respLen) {
                    totalRead += inStream.read(respBuf, totalRead, respLen - totalRead)
                }

                val json         = JSONObject(String(respBuf, Charsets.UTF_8))
                val heard        = json.optString("heard", "")
                val reply        = json.optString("reply_urdu", "")
                val needsConfirm = json.optBoolean("needs_confirmation", false)

                withContext(Dispatchers.Main) {
                    tvHeard.text = heard.ifEmpty { "—" }
                    tvReply.text = reply.ifEmpty { "—" }
                    if (needsConfirm) {
                        setStatus("● HOLD TO CONFIRM  /  RELEASE = CANCEL", "#FFAA00")
                    } else {
                        setStatus("● CONNECTED  —  HOLD TO TALK", "#00FF88")
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    setStatus("● ERROR: ${e.message}", "#FF4444")
                    disconnect()
                }
            }
        }
    }

    // ── WAV builder ───────────────────────────────────────────────────────────

    private fun buildWav(pcm: ByteArray): ByteArray {
        val out      = ByteArrayOutputStream()
        val dataLen  = pcm.size
        val byteRate = SAMPLE_RATE * 2  // mono, 16-bit

        fun le32(v: Int) = byteArrayOf(
            (v and 0xFF).toByte(), ((v shr 8) and 0xFF).toByte(),
            ((v shr 16) and 0xFF).toByte(), ((v shr 24) and 0xFF).toByte()
        )
        fun le16(v: Int) = byteArrayOf(
            (v and 0xFF).toByte(), ((v shr 8) and 0xFF).toByte()
        )

        out.write("RIFF".toByteArray())
        out.write(le32(36 + dataLen))
        out.write("WAVE".toByteArray())
        out.write("fmt ".toByteArray())
        out.write(le32(16))
        out.write(le16(1))         // PCM
        out.write(le16(1))         // mono
        out.write(le32(SAMPLE_RATE))
        out.write(le32(byteRate))
        out.write(le16(2))         // block align
        out.write(le16(16))        // bits per sample
        out.write("data".toByteArray())
        out.write(le32(dataLen))
        out.write(pcm)
        return out.toByteArray()
    }

    private fun rmsAmplitude(buf: ByteArray, len: Int): Float {
        var sum = 0.0
        val sampleCount = len / 2
        for (i in 0 until sampleCount) {
            val sample = ((buf[i * 2].toInt() and 0xFF) or ((buf[i * 2 + 1].toInt() and 0xFF) shl 8))
                .toShort().toDouble()
            sum += sample * sample
        }
        return (sqrt(sum / sampleCount) / 32768.0).toFloat().coerceIn(0f, 1f)
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private fun setStatus(text: String, hex: String) {
        tvStatus.text = text
        tvStatus.setTextColor(Color.parseColor(hex))
    }

    private fun requestMicPermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                this, arrayOf(Manifest.permission.RECORD_AUDIO), REQUEST_MIC
            )
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
        runCatching { socket?.close() }
    }
}
