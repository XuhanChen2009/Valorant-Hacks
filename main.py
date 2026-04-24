import threading
import time
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from discord_webhook import DiscordWebhook, DiscordEmbed

Window.clearcolor = (0.1, 0.1, 0.1, 1)

# --- KONFIGURATION ---
WEBHOOK_URL = "DEIN_WEBHOOK_HIER"
APP_AT      = "DEIN_TOKEN_HIER"
MIN_PRIZE   = 500
REFRESH_RATE = 15

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Mobile Safari/537.36"
)


class RainNotifierLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=12, spacing=8, **kwargs)

        self.running   = False
        self.thread    = None
        self.last_id   = None
        self.session   = None

        # ── Titel ──────────────────────────────────────────────
        self.add_widget(Label(
            text="🌧️ Bloxflip Rain Notifier",
            font_size="22sp",
            bold=True,
            size_hint_y=None,
            height=50,
            color=(1, 0.78, 0, 1),
        ))

        # ── Token-Eingabe ──────────────────────────────────────
        self.token_input = TextInput(
            hint_text="app.at Token hier einfügen",
            text=APP_AT if APP_AT != "DEIN_TOKEN_HIER" else "",
            multiline=False,
            size_hint_y=None,
            height=44,
            background_color=(0.15, 0.15, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
        )
        self.add_widget(self.token_input)

        # ── Webhook-Eingabe ────────────────────────────────────
        self.webhook_input = TextInput(
            hint_text="Discord Webhook URL",
            text=WEBHOOK_URL if WEBHOOK_URL != "DEIN_WEBHOOK_HIER" else "",
            multiline=False,
            size_hint_y=None,
            height=44,
            background_color=(0.15, 0.15, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
        )
        self.add_widget(self.webhook_input)

        # ── Start / Stop ───────────────────────────────────────
        self.btn = Button(
            text="▶  Starten",
            size_hint_y=None,
            height=52,
            background_color=(0, 0.6, 0.2, 1),
            font_size="18sp",
        )
        self.btn.bind(on_press=self.toggle)
        self.add_widget(self.btn)

        # ── Status-Label ───────────────────────────────────────
        self.status_label = Label(
            text="⏸ Gestoppt",
            size_hint_y=None,
            height=36,
            color=(0.7, 0.7, 0.7, 1),
        )
        self.add_widget(self.status_label)

        # ── Log-Bereich ────────────────────────────────────────
        scroll = ScrollView()
        self.log_label = Label(
            text="Bereit.\n",
            valign="top",
            halign="left",
            markup=True,
            size_hint_y=None,
            color=(0.9, 0.9, 0.9, 1),
        )
        self.log_label.bind(texture_size=lambda inst, val: setattr(inst, "size", val))
        scroll.add_widget(self.log_label)
        self.add_widget(scroll)

    # ── Hilfsfunktionen ────────────────────────────────────────
    def log(self, msg):
        def _update(dt):
            ts = time.strftime("%H:%M:%S")
            self.log_label.text += f"[{ts}] {msg}\n"
        Clock.schedule_once(_update)

    def set_status(self, txt, color=(1, 1, 1, 1)):
        def _update(dt):
            self.status_label.text  = txt
            self.status_label.color = color
        Clock.schedule_once(_update)

    # ── Start / Stop ───────────────────────────────────────────
    def toggle(self, *_):
        if self.running:
            self.running = False
            self.btn.text             = "▶  Starten"
            self.btn.background_color = (0, 0.6, 0.2, 1)
            self.set_status("⏸ Gestoppt", (0.7, 0.7, 0.7, 1))
        else:
            token   = self.token_input.text.strip()
            webhook = self.webhook_input.text.strip()
            if not token or not webhook:
                self.log("[COLOR=ff4444]❌ Bitte Token & Webhook eintragen![/COLOR]")
                return

            self.running              = True
            self.btn.text             = "⏹  Stoppen"
            self.btn.background_color = (0.7, 0.1, 0.1, 1)
            self.set_status("🔄 Läuft ...", (0, 1, 0.4, 1))
            self._build_session(token)
            self.thread = threading.Thread(target=self._loop,
                                           args=(token, webhook),
                                           daemon=True)
            self.thread.start()

    def _build_session(self, token):
        self.session = requests.Session()
        self.session.cookies.update({"app.at": token})
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "x-currency": "ROCOINS",
            "Origin": "https://bloxflip.com",
            "Referer": "https://bloxflip.com/profile",
        })

    # ── Haupt-Loop (läuft im Hintergrund-Thread) ──────────────
    def _loop(self, token, webhook_url):
        self.log("✅ Suche nach Rain gestartet ...")
        self.log(f"Mindestbetrag: {MIN_PRIZE} R$  |  Intervall: {REFRESH_RATE}s")

        while self.running:
            rain = self._check_rain()
            if rain:
                rid = rain.get("id", "no_id")
                if rid != self.last_id:
                    self._handle_rain(rain, webhook_url)
                    self.last_id = rid
                    time.sleep(30)
            time.sleep(REFRESH_RATE)

        self.log("⏹ Gestoppt.")

    def _check_rain(self):
        try:
            r = self.session.get(
                "https://bloxflip.com/api/chat/history", timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                rain = data.get("rain", {})
                if rain.get("active") and rain.get("prize", 0) >= MIN_PRIZE:
                    return rain
            elif r.status_code == 401:
                self.log("[COLOR=ff4444]❌ 401: Token ungültig / abgelaufen![/COLOR]")
            elif r.status_code == 403:
                self.log("[COLOR=ff9900]⚠️ 403: Cloudflare blockiert.[/COLOR]")
            else:
                self.log(f"⚠️ Status: {r.status_code}")
        except Exception as e:
            self.log(f"⚠️ Netzwerkfehler: {e}")
        return None

    def _handle_rain(self, rain, webhook_url):
        prize    = rain.get("prize", 0)
        players  = rain.get("players", 0)
        ms_left  = rain.get("timeLeft", 0)
        expiry   = int(time.time() + ms_left / 1000)

        self.log(f"🌧️ RAIN! Betrag: {prize} R$  |  Spieler: {players}")

        for i in range(10):
            try:
                wh = DiscordWebhook(url=webhook_url, content="@everyone")
                if i == 0:
                    emb = DiscordEmbed(
                        title="🌧️ Bloxflip Rain Alarm!",
                        url="https://bloxflip.com",
                        color=0xFFC800,
                    )
                    emb.add_embed_field(name="Betrag",     value=f"{prize:,} R$")
                    emb.add_embed_field(name="Teilnehmer", value=str(players))
                    emb.add_embed_field(name="Endet",      value=f"<t:{expiry}:R>")
                    emb.set_timestamp()
                    wh.add_embed(emb)
                wh.execute()
                self.log(f"  → Ping [{i+1}/10] gesendet")
                if i < 9:
                    time.sleep(5)
            except Exception as e:
                self.log(f"❌ Webhook-Fehler ({i+1}): {e}")


class BloxflipApp(App):
    def build(self):
        self.title = "Bloxflip Rain Notifier"
        return RainNotifierLayout()


if __name__ == "__main__":
    BloxflipApp().run()
