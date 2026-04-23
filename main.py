import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.clock import Clock
import requests
from urllib.parse import urlparse, parse_qs
import threading
import urllib3

# SSL Sertifika uyarılarını Android'de kapatıyoruz (PHP'deki verify=false karşılığı)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class IPTVChecker(App):
    def build(self):
        self.title = "Deathless Pro V2"
        self.hits = []
        
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        layout.add_widget(Label(text="DEATHLESS PRO CHECKER", font_size='22sp', color=(0.38, 0.4, 0.94, 1)))
        
        self.stats = Label(text="Toplam: 0 | HIT: 0 | Pasif: 0", size_hint_y=None, height=40)
        layout.add_widget(self.stats)

        self.txt_input = TextInput(
            hint_text="M3U Linklerini buraya yapıştırın...",
            multiline=True,
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(1, 1, 1, 1),
            font_name='Roboto' # Android standart fontu
        )
        layout.add_widget(self.txt_input)

        self.lbl_status = Label(text="Durum: Bekleniyor...", size_hint_y=None, height=30, font_size='12sp')
        layout.add_widget(self.lbl_status)

        btn = Button(text="TARAMAYI BAŞLAT", size_hint_y=None, height=60, background_color=(0.13, 0.77, 0.36, 1))
        btn.bind(on_press=self.start_check_thread)
        layout.add_widget(btn)

        return layout

    def start_check_thread(self, instance):
        threading.Thread(target=self.process_links, daemon=True).start()

    def process_links(self):
        content = self.txt_input.text.strip()
        if not content:
            self.update_status("Link girmediniz!")
            return

        # Linkleri ayıkla
        lines = [l.strip() for l in content.splitlines() if "username=" in l]
        total = len(lines)
        hit_count = 0
        bad_count = 0

        # PHP'deki CURL oturumu gibi bir Session oluşturuyoruz
        session = requests.Session()
        session.verify = False # SSL kontrolünü kapat
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*'
        })

        for link in lines:
            if self.check_account(session, link):
                hit_count += 1
                self.hits.append(link)
                self.save_hit(link)
            else:
                bad_count += 1
            
            self.update_stats(total, hit_count, bad_count)
        
        self.update_status(f"Tarama Bitti! {hit_count} HIT kaydedildi.")

    def check_account(self, session, m3u):
        try:
            parsed = urlparse(m3u)
            qs = parse_qs(parsed.query)
            user = qs.get('username', [None])[0]
            passw = qs.get('password', [None])[0]
            
            if not user or not passw: return False

            # PHP'deki apiTarget'ı tam olarak kuruyoruz
            api_url = f"{parsed.scheme}://{parsed.netloc}/player_api.php?username={user}&password={passw}"
            
            # allow_redirects=True -> PHP'deki CURLOPT_FOLLOWLOCATION karşılığıdır
            r = session.get(api_url, timeout=12, allow_redirects=True)
            
            if r.status_code == 200:
                # Bazı paneller JSON yerine düz metin döner, her ikisini de kontrol et
                try:
                    data = r.json()
                    if data.get('user_info', {}).get('status', '').lower() == "active":
                        return True
                except:
                    # JSON hatası verirse metin içinde "Active" ara
                    if '"status":"Active"' in r.text or '"status":"active"' in r.text:
                        return True
        except:
            pass
        return False

    def save_hit(self, link):
        try:
            # Android Download klasörüne PHP'deki isimle kaydet
            path = "/storage/emulated/0/Download/hit-iptv-m3u.txt"
            with open(path, "a", encoding="utf-8") as f:
                f.write(link + "\n")
        except:
            pass

    def update_stats(self, t, h, b):
        Clock.schedule_once(lambda dt: setattr(self.stats, 'text', f"Toplam: {t} | HIT: {h} | Pasif: {b}"))

    def update_status(self, text):
        Clock.schedule_once(lambda dt: setattr(self.lbl_status, 'text', text))

if __name__ == "__main__":
    IPTVChecker().run()
        
