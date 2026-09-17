"""Translated screen labels for DGUS Reloaded 2.0.

The language index stored by Marlin (DGUS_Addr::LANGUAGE) is the position in LANGS.
Each entry of S is a string per language, in the order of LANGS.
"""

LANGS = ['en', 'fr', 'de', 'es', 'it', 'pt', 'nl', 'pl', 'tr', 'ru', 'ar', 'hi', 'zh', 'ja', 'ko', 'id']

_T = {
    # key: en | fr | de | es | it | pt | nl | pl | tr | ru | ar | hi | zh | ja | ko | id
    'files': "Files|Fichiers|Dateien|Archivos|File|Arquivos|Bestanden|Pliki|Dosyalar|Файлы|الملفات|फ़ाइलें|文件|ファイル|파일|Berkas",
    'printing': "Printing|Impression|Druck|Imprimiendo|Stampa|Imprimindo|Printen|Drukowanie|Yazdırılıyor|Печать|جارٍ الطباعة|प्रिंटिंग|打印中|印刷中|인쇄 중|Mencetak",
    'adjust': "Adjust print|Ajuster l'impression|Druck anpassen|Ajustar impresión|Regola stampa|Ajustar impressão|Print aanpassen|Dostosuj wydruk|Baskıyı ayarla|Настройка печати|ضبط الطباعة|प्रिंट समायोजित करें|调整打印|印刷の調整|인쇄 조정|Sesuaikan cetak",
    'adjust_btn': "Adjust|Ajuster|Anpassen|Ajustar|Regola|Ajustar|Aanpassen|Dostosuj|Ayarla|Настроить|ضبط|समायोजित|调整|調整|조정|Sesuaikan",
    'finished': "Print finished|Impression terminée|Druck fertig|Impresión terminada|Stampa completata|Impressão concluída|Print voltooid|Wydruk zakończony|Baskı tamamlandı|Печать завершена|اكتملت الطباعة|प्रिंट पूरा हुआ|打印完成|印刷完了|인쇄 완료|Cetak selesai",
    'temperature': "Temperature|Température|Temperatur|Temperatura|Temperatura|Temperatura|Temperatuur|Temperatura|Sıcaklık|Температура|الحرارة|तापमान|温度|温度|온도|Suhu",
    'fan': "Fan|Ventilateur|Lüfter|Ventilador|Ventola|Ventoinha|Ventilator|Wentylator|Fan|Вентилятор|المروحة|पंखा|风扇|ファン|팬|Kipas",
    'settings': "Settings|Réglages|Einstellungen|Ajustes|Impostazioni|Configurações|Instellingen|Ustawienia|Ayarlar|Настройки|الإعدادات|सेटिंग्स|设置|設定|설정|Pengaturan",
    'more': "More|Plus|Mehr|Más|Altro|Mais|Meer|Więcej|Diğer|Ещё|المزيد|अधिक|更多|その他|더보기|Lainnya",
    'leveling': "Leveling|Nivellement|Nivellierung|Nivelación|Livellamento|Nivelamento|Nivelleren|Poziomowanie|Tabla ayarı|Выравнивание|تسوية السرير|लेवलिंग|调平|レベリング|레벨링|Perataan",
    'z_offset': "Z offset|Décalage Z|Z-Versatz|Offset Z|Offset Z|Offset Z|Z-offset|Offset Z|Z ofseti|Смещение Z|إزاحة Z|Z ऑफ़सेट|Z 偏移|Zオフセット|Z 오프셋|Offset Z",
    'manual': "Manual|Manuel|Manuell|Manual|Manuale|Manual|Handmatig|Ręczne|Manuel|Вручную|يدوي|मैनुअल|手动|手動|수동|Manual",
    'automatic': "Automatic|Automatique|Automatisch|Automático|Automatico|Automático|Automatisch|Automatyczne|Otomatik|Автоматически|تلقائي|स्वचालित|自动|自動|자동|Otomatis",
    'probing': "Probing|Palpage|Abtasten|Palpado|Tastatura|Sondagem|Meten|Sondowanie|Ölçüm|Зондирование|جارٍ القياس|प्रोबिंग|探测中|プロービング|프로빙|Probing",
    'filament': "Filament|Filament|Filament|Filamento|Filamento|Filamento|Filament|Filament|Filament|Филамент|الخيط|फिलामेंट|耗材|フィラメント|필라멘트|Filamen",
    'move': "Move|Déplacer|Bewegen|Mover|Muovi|Mover|Bewegen|Ruch|Hareket|Перемещение|تحريك|मूव|移动|移動|이동|Gerak",
    'gcode': "G-code|G-code|G-Code|G-code|G-code|G-code|G-code|G-code|G-code|G-code|G-code|G-code|G-code|G-code|G-code|G-code",
    'pid': "PID tuning|Réglage PID|PID-Abgleich|Ajuste PID|Taratura PID|Calibração PID|PID-afstelling|Strojenie PID|PID ayarı|Настройка PID|ضبط PID|PID ट्यूनिंग|PID 调节|PID調整|PID 튜닝|Penyetelan PID",
    'volume': "Volume|Volume|Lautstärke|Volumen|Volume|Volume|Volume|Głośność|Ses|Громкость|الصوت|वॉल्यूम|音量|音量|음량|Volume",
    'brightness': "Brightness|Luminosité|Helligkeit|Brillo|Luminosità|Brilho|Helderheid|Jasność|Parlaklık|Яркость|السطوع|चमक|亮度|明るさ|밝기|Kecerahan",
    'information': "Information|Informations|Informationen|Información|Informazioni|Informações|Informatie|Informacje|Bilgi|Информация|معلومات|जानकारी|信息|情報|정보|Informasi",
    'wait': "Please wait|Patientez|Bitte warten|Espere|Attendere|Aguarde|Even geduld|Proszę czekać|Lütfen bekleyin|Подождите|يرجى الانتظار|कृपया प्रतीक्षा करें|请稍候|お待ちください|잠시 기다려 주세요|Harap tunggu",
    'power_loss': "Power loss|Coupure de courant|Stromausfall|Corte de luz|Interruzione|Queda de energia|Stroomuitval|Zanik zasilania|Elektrik kesintisi|Сбой питания|انقطاع الكهرباء|बिजली कटौती|断电|停電|정전|Listrik padam",
    'error': "Error|Erreur|Fehler|Error|Errore|Erro|Fout|Błąd|Hata|Ошибка|خطأ|त्रुटि|错误|エラー|오류|Kesalahan",
    't_ext': "Extruder temperature|Température de l'extrudeur|Extrudertemperatur|Temperatura del extrusor|Temperatura estrusore|Temperatura do extrusor|Extrudertemperatuur|Temperatura ekstrudera|Ekstrüder sıcaklığı|Температура экструдера|حرارة الطارد|एक्सट्रूडर तापमान|挤出头温度|エクストルーダー温度|익스트루더 온도|Suhu ekstruder",
    't_bed': "Bed temperature|Température du plateau|Betttemperatur|Temperatura de la cama|Temperatura piatto|Temperatura da mesa|Bedtemperatuur|Temperatura stołu|Tabla sıcaklığı|Температура стола|حرارة السرير|बेड तापमान|热床温度|ベッド温度|베드 온도|Suhu bed",
    'status': "Status|Statut|Status|Estado|Stato|Estado|Status|Status|Durum|Статус|الحالة|स्थिति|状态|ステータス|상태|Status",
    'print': "Print|Imprimer|Drucken|Imprimir|Stampa|Imprimir|Printen|Drukuj|Yazdır|Печать|طباعة|प्रिंट|打印|印刷|인쇄|Cetak",
    'extruder': "Extruder|Extrudeur|Extruder|Extrusor|Estrusore|Extrusor|Extruder|Ekstruder|Ekstrüder|Экструдер|الطارد|एक्सट्रूडर|挤出头|エクストルーダー|익스트루더|Ekstruder",
    'bed': "Bed|Plateau|Bett|Cama|Piatto|Mesa|Bed|Stół|Tabla|Стол|السرير|बेड|热床|ベッド|베드|Bed",
    'target': "Target|Consigne|Soll|Objetivo|Obiettivo|Alvo|Doel|Docelowa|Hedef|Цель|الهدف|लक्ष्य|目标|目標|목표|Target",
    'cool': "Cool down|Refroidir|Abkühlen|Enfriar|Raffredda|Arrefecer|Afkoelen|Schłodź|Soğut|Охладить|تبريد|ठंडा करें|冷却|冷却|냉각|Dinginkan",
    'presets': "Preheat|Préchauffe|Vorheizen|Precalentar|Preriscaldo|Pré-aquecer|Voorverwarmen|Podgrzej|Ön ısıtma|Преднагрев|تسخين مسبق|प्रीहीट|预热|予熱|예열|Panaskan",
    'fan_speed': "Fan speed|Vitesse du ventilateur|Lüftergeschwindigkeit|Velocidad del ventilador|Velocità ventola|Velocidade da ventoinha|Ventilatorsnelheid|Prędkość wentylatora|Fan hızı|Скорость вентилятора|سرعة المروحة|पंखे की गति|风扇速度|ファン速度|팬 속도|Kecepatan kipas",
    'feedrate': "Speed|Vitesse|Geschwindigkeit|Velocidad|Velocità|Velocidade|Snelheid|Prędkość|Hız|Скорость|السرعة|गति|速度|速度|속도|Kecepatan",
    'flowrate': "Flow|Débit|Fluss|Flujo|Flusso|Fluxo|Flow|Przepływ|Akış|Поток|التدفق|फ़्लो|流量|流量|유량|Aliran",
    'z_height': "Z height|Hauteur Z|Z-Höhe|Altura Z|Altezza Z|Altura Z|Z-hoogte|Wysokość Z|Z yüksekliği|Высота Z|ارتفاع Z|Z ऊँचाई|Z 高度|Z高さ|Z 높이|Tinggi Z",
    'elapsed': "Elapsed|Durée|Dauer|Tiempo|Durata|Decorrido|Verstreken|Czas|Geçen süre|Прошло|المنقضي|बीता समय|已用时间|経過時間|경과 시간|Durasi",
    'progress': "Progress|Progression|Fortschritt|Progreso|Avanzamento|Progresso|Voortgang|Postęp|İlerleme|Прогресс|التقدم|प्रगति|进度|進捗|진행률|Progres",
    'abort': "Stop|Arrêter|Abbrechen|Detener|Interrompi|Parar|Stoppen|Zatrzymaj|Durdur|Стоп|إيقاف|रोकें|停止|停止|정지|Hentikan",
    'home': "Home|Accueil|Start|Inicio|Home|Início|Start|Start|Ana sayfa|Главная|الرئيسية|होम|主页|ホーム|홈|Beranda",
    'steppers': "Steppers|Moteurs|Motoren|Motores|Motori|Motores|Motoren|Silniki|Motorlar|Моторы|المحركات|मोटर|电机|モーター|모터|Motor",
    'step': "Step|Pas|Schritt|Paso|Passo|Passo|Stap|Krok|Adım|Шаг|الخطوة|स्टेप|步长|ステップ|단계|Langkah",
    'home_axes': "Home|Origine|Referenz|Origen|Home|Origem|Home|Bazowanie|Sıfırla|Домой|الأصل|होम|归零|原点|원점|Home",
    'probe': "Probe|Palper|Abtasten|Palpar|Tasta|Sondar|Meten|Sonduj|Ölç|Зонд|قياس|प्रोब|探测|プローブ|프로브|Probe",
    'mesh': "Mesh|Maillage|Netz|Malla|Griglia|Malha|Mesh|Siatka|Ağ|Сетка|الشبكة|मेश|网格|メッシュ|메시|Mesh",
    'length': "Length|Longueur|Länge|Longitud|Lunghezza|Comprimento|Lengte|Długość|Uzunluk|Длина|الطول|लंबाई|长度|長さ|길이|Panjang",
    'retract': "Retract|Rétracter|Zurückziehen|Retraer|Ritrai|Retrair|Terugtrekken|Wycofaj|Geri çek|Втянуть|سحب|रिट्रैक्ट|回抽|引き戻し|후퇴|Tarik",
    'extrude': "Extrude|Extruder|Extrudieren|Extruir|Estrudi|Extrudar|Extruderen|Wytłocz|Ekstrüde et|Выдавить|بثق|एक्सट्रूड|挤出|押し出し|압출|Ekstrusi",
    'clear': "Clear|Effacer|Löschen|Borrar|Cancella|Limpar|Wissen|Wyczyść|Temizle|Очистить|مسح|साफ़ करें|清除|クリア|지우기|Hapus",
    'send': "Send|Envoyer|Senden|Enviar|Invia|Enviar|Versturen|Wyślij|Gönder|Отправить|إرسال|भेजें|发送|送信|전송|Kirim",
    'gcode_hint': "Tap the field to type a command|Touchez le champ pour saisir une commande|Feld antippen, um einen Befehl einzugeben|Toque el campo para escribir un comando|Tocca il campo per scrivere un comando|Toque no campo para digitar um comando|Tik op het veld om een commando te typen|Dotknij pola, aby wpisać polecenie|Komut yazmak için alana dokunun|Коснитесь поля, чтобы ввести команду|المس الحقل لكتابة أمر|कमांड लिखने के लिए फ़ील्ड पर टैप करें|点击输入框输入命令|欄をタップしてコマンドを入力|필드를 눌러 명령을 입력하세요|Ketuk kolom untuk mengetik perintah",
    'pid_temp': "Target temperature|Température cible|Zieltemperatur|Temperatura objetivo|Temperatura target|Temperatura alvo|Doeltemperatuur|Temperatura docelowa|Hedef sıcaklık|Целевая температура|الحرارة المستهدفة|लक्ष्य तापमान|目标温度|目標温度|목표 온도|Suhu target",
    'cycles': "Cycles|Cycles|Zyklen|Ciclos|Cicli|Ciclos|Cycli|Cykle|Döngü|Циклы|الدورات|चक्र|循环次数|サイクル|사이클|Siklus",
    'run': "Start|Lancer|Starten|Iniciar|Avvia|Iniciar|Starten|Uruchom|Başlat|Запуск|تشغيل|शुरू करें|开始|開始|시작|Mulai",
    'machine': "Machine|Machine|Maschine|Máquina|Macchina|Máquina|Machine|Maszyna|Makine|Принтер|الآلة|मशीन|机器|機種|기기|Mesin",
    'build_volume': "Build volume|Volume d'impression|Bauraum|Volumen|Volume di stampa|Volume de impressão|Bouwvolume|Obszar roboczy|Baskı hacmi|Область печати|حجم الطباعة|बिल्ड वॉल्यूम|打印尺寸|造形サイズ|출력 크기|Volume cetak",
    'version': "Marlin version|Version Marlin|Marlin-Version|Versión Marlin|Versione Marlin|Versão Marlin|Marlin-versie|Wersja Marlin|Marlin sürümü|Версия Marlin|إصدار Marlin|Marlin संस्करण|Marlin 版本|Marlin バージョン|Marlin 버전|Versi Marlin",
    'prints': "Prints|Impressions|Drucke|Impresiones|Stampe|Impressões|Prints|Wydruki|Baskılar|Печати|المطبوعات|प्रिंट|打印次数|印刷回数|출력 수|Cetakan",
    'completed': "Finished|Terminées|Fertig|Terminadas|Completate|Concluídas|Voltooid|Ukończone|Tamamlanan|Завершено|المكتملة|पूर्ण|已完成|完了|완료|Selesai",
    'print_time': "Print time|Temps d'impression|Druckzeit|Tiempo de impresión|Tempo di stampa|Tempo de impressão|Printtijd|Czas druku|Baskı süresi|Время печати|وقت الطباعة|प्रिंट समय|打印时间|印刷時間|출력 시간|Waktu cetak",
    'longest': "Longest print|La plus longue|Längster Druck|La más larga|La più lunga|Mais longa|Langste print|Najdłuższy wydruk|En uzun baskı|Самая долгая|الأطول|सबसे लंबा प्रिंट|最长打印|最長印刷|최장 출력|Cetak terlama",
    'filament_used': "Filament used|Filament utilisé|Filament verbraucht|Filamento usado|Filamento usato|Filamento usado|Filament gebruikt|Zużyty filament|Kullanılan filament|Расход филамента|الخيط المستخدم|प्रयुक्त फिलामेंट|耗材用量|使用フィラメント|사용한 필라멘트|Filamen terpakai",
    'reset_eeprom': "Reset settings|Réinitialiser|Zurücksetzen|Restablecer|Ripristina|Redefinir|Resetten|Resetuj|Sıfırla|Сброс настроек|إعادة الضبط|रीसेट करें|恢复默认|リセット|초기화|Atur ulang",
    'resume_q': "Resume the print?|Reprendre l'impression ?|Druck fortsetzen?|¿Reanudar la impresión?|Riprendere la stampa?|Retomar a impressão?|Print hervatten?|Wznowić drukowanie?|Baskıya devam edilsin mi?|Продолжить печать?|استئناف الطباعة؟|प्रिंट फिर से शुरू करें?|继续打印？|印刷を再開しますか？|인쇄를 재개할까요?|Lanjutkan cetak?",
    'resume': "Resume|Reprendre|Fortsetzen|Reanudar|Riprendi|Retomar|Hervatten|Wznów|Devam et|Продолжить|استئناف|जारी रखें|继续|再開|재개|Lanjutkan",
    'cancel': "Cancel|Annuler|Abbrechen|Cancelar|Annulla|Cancelar|Annuleren|Anuluj|İptal|Отмена|إلغاء|रद्द करें|取消|キャンセル|취소|Batal",
    'sensor': "Filament sensor|Capteur de filament|Filamentsensor|Sensor de filamento|Sensore filamento|Sensor de filamento|Filamentsensor|Czujnik filamentu|Filament sensörü|Датчик филамента|حساس الخيط|फिलामेंट सेंसर|耗材传感器|フィラメントセンサー|필라멘트 센서|Sensor filamen",
    'runout': "Runout detection|Fin de filament|Filamentende|Fin de filamento|Fine filamento|Fim de filamento|Filament op|Koniec filamentu|Filament bitti|Окончание филамента|نفاد الخيط|फिलामेंट खत्म|断料检测|フィラメント切れ|필라멘트 소진|Filamen habis",
    'runout_sub': "Switch on D8|Détecteur sur D8|Schalter an D8|Interruptor en D8|Interruttore su D8|Interruptor em D8|Schakelaar op D8|Przełącznik na D8|D8 üzerinde anahtar|Датчик на D8|مفتاح على D8|D8 पर स्विच|D8 上的开关|D8 のスイッチ|D8 스위치|Sakelar di D8",
    'jam': "Jam detection|Détection de bourrage|Stauerkennung|Detección de atasco|Rilevamento inceppamento|Detecção de entupimento|Verstoppingsdetectie|Wykrywanie zatoru|Tıkanma algılama|Обнаружение застревания|كشف الانسداد|जाम का पता लगाना|堵料检测|詰まり検出|막힘 감지|Deteksi macet",
    'jam_sub': "BTT Smart Filament Sensor on D9|BTT Smart Filament Sensor sur D9|BTT Smart Filament Sensor an D9|BTT Smart Filament Sensor en D9|BTT Smart Filament Sensor su D9|BTT Smart Filament Sensor em D9|BTT Smart Filament Sensor op D9|BTT Smart Filament Sensor na D9|D9 üzerinde BTT Smart Filament Sensor|BTT Smart Filament Sensor на D9|BTT Smart Filament Sensor على D9|D9 पर BTT Smart Filament Sensor|D9 上的 BTT Smart Filament Sensor|D9 の BTT Smart Filament Sensor|D9의 BTT Smart Filament Sensor|BTT Smart Filament Sensor di D9",
    'jam_len': "Jam length|Longueur de bourrage|Staulänge|Longitud de atasco|Lunghezza inceppamento|Comprimento de entupimento|Verstoppingslengte|Długość zatoru|Tıkanma uzunluğu|Длина застревания|طول الانسداد|जाम लंबाई|堵料长度|詰まり長さ|막힘 길이|Panjang macet",
    'save': "Save|Enregistrer|Speichern|Guardar|Salva|Salvar|Opslaan|Zapisz|Kaydet|Сохранить|حفظ|सहेजें|保存|保存|저장|Simpan",
}
_T['loaded'] = _T['filament']

S = {}
for _k, _v in _T.items():
    _parts = _v.split('|')
    assert len(_parts) == len(LANGS), (_k, len(_parts))
    S[_k] = tuple(_parts)
