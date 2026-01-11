# Plan Implementacji - Google Photos Archiver

## Zakres Fazy 1: Tylko Zdjęcia

### Założenia
- ✅ Skupiamy się TYLKO na Google Photos
- ✅ WSZYSTKIE zdjęcia są przenoszone na dysk (bez względu na datę)
- ✅ **Format backupu zgodny z digiKam** (pojedyncze pliki + XMP sidecars + opcjonalnie SQLite)
- ✅ **Zbieramy WSZYSTKIE metadane dostępne z Google Photos API**
  - Geolokalizacja, albumy, opisy, dane kamery, wymiary, daty - wszystko!
- ✅ Sprawdzamy które zdjęcia są w albumach (dla nazewnictwa plików + XMP tags)
- ✅ Inkrementalna synchronizacja - pomijamy zdjęcia już skopiowane (nie zmieniają się)
- ✅ Usuwanie z Google to ODDZIELNY proces (osobny etap/skrypt)
  - Usuwane są TYLKO zdjęcia starsze niż 2 lata
  - Usuwane są TYLKO zdjęcia NIE będące w żadnym albumie
  - Poprzedzone ZAWSZE kalkulacją i oznaczeniem plików

---

## Przepływy Pracy

System obsługuje trzy niezależne procesy, które mogą być wykonywane alternatywnie:

1. **Proces Główny (DEFAULT)** - `python main.py`
   - Etapy 1-5: Backup, pobieranie i oznaczanie plików
   - Wykonywany domyślnie

2. **Usuwanie Flagi (OPCJONALNY)** - `python clear_marks.py`
   - Czyści oznaczenia marked_for_deletion
   - Wykonywany niezależnie, pomija Etapy 1-5

3. **Usuwanie z Google Photos (OPCJONALNY)** - `python delete_from_google.py`
   - Usuwa zdjęcia z Google Photos
   - Wykonywany niezależnie, pomija Etapy 1-5

---

### Diagram Przepływów Pracy

```
GOOGLE PHOTOS ARCHIVER - PRZEPŁYWY PRACY
│
├── [PROCES 1] Główny (DEFAULT)
│   │   Komenda: python main.py
│   │
│   ├── Etap 1: Uwierzytelnienie
│   │
│   ├── Etap 2: Przygotowanie Struktury
│   │   ├── 2.1: Organizacja na Dysku
│   │   └── 2.2: Utworzenie Bazy Metadanych
│   │
│   ├── Etap 3: Odczyt Meta Danych z Google
│   │   ├── 3.1: Pobranie Metadanych Zdjęć
│   │   ├── 3.2: Pobranie Albumów
│   │   └── 3.3: Sprawdzenie Co Już Mamy
│   │
│   ├── Etap 4: Pobieranie Danych
│   │   ├── 4.1: Pobieranie Zdjęć (batche 50 + XMP + commit)
│   │   └── 4.2: Weryfikacja
│   │
│   └── Etap 5: Oznaczanie Plików do Usunięcia
│       ├── 5a: Kalkulacja Usuwania (tylko raport)
│       └── 5b: Oznaczenie Zdjęć (XMP + baza)
│
├── [PROCES 2] Usuwanie Flagi (OPCJONALNY)
│   │   Komenda: python clear_marks.py
│   │
│   └── Czyszczenie oznaczeń marked_for_deletion
│       ├── UPDATE photos SET marked_for_deletion = 0
│       ├── Usunięcie tagów z Google Photos (opcjonalnie)
│       └── Usunięcie marked_for_deletion.json
│
└── [PROCES 3] Usuwanie z Google Photos (OPCJONALNY)
    │   Komenda: python delete_from_google.py
    │
    └── Usunięcie zdjęć z Google Photos
        ├── Weryfikacja: marked_for_deletion = 1 + tag w XMP
        ├── Usunięcie z Google (batche 50)
        ├── Aktualizacja XMP (tag: DELETED_FROM_GOOGLE)
        └── UPDATE photos SET deleted_from_google = 1
```

---

### Proces 1: Główny (DEFAULT)
**Komenda:** `python main.py`

**Opis:** Backup wszystkich zdjęć z Google Photos + przygotowanie do usunięcia

---

#### Etap 1: Uwierzytelnienie
**Cel:** Połączenie z Google Photos API

**Działania:**
- Wczytanie `credentials.json` (OAuth 2.0)
- Utworzenie tokenu dostępu (`token.json`)
- Zapisanie tokenu dla przyszłych uruchomień

**Output:**
- Połączenie z Google Photos API
- Token ważny przez X dni

---

#### Etap 2: Przygotowanie Struktury

##### Etap 2.1: Organizacja na Dysku
**Cel:** Płaska struktura na `/mnt/data/google-archiver/` zgodna z digiKam

**Uwaga:** Jednorazowy zabieg - kolejne wywołania nie robią nic, bo struktura plików i baza już istnieją

**Wymaganie kompatybilności:**
- ✅ digiKam może zaimportować `photos/` folder bez problemów
- ✅ XMP sidecars obok każdego pliku (opcjonalnie, ale zalecane)
- ✅ EXIF zawiera wszystkie metadane (data, geolokalizacja, kamera)
- ✅ SQLite database dla szybkiego przeszukiwania (niezależna od digiKam)

**Struktura:**
```
/mnt/data/google-archiver/
├── photos/                        # WSZYSTKIE zdjęcia w jednym katalogu (płaskim)
│   ├── AlbumName_IMG_123.jpg       # Zdjęcie w albumie
│   ├── AlbumName_IMG_123.xmp       # XMP sidecar: tagi albumów, geolokacja
│   ├── AlbumName_VID_456.mp4       # Wideo w albumie
│   ├── IMG_20220115_123456.jpg     # Zdjęcie NIE w albumie
│   └── PXL_20230520_084523.jpg     # Zdjęcie NIE w albumie
└── metadata/
    ├── photos.db                   # SQLite: PEŁNA baza metadanych (albumy, geo, wszystko)
    ├── archive_index.json          # Backup metadanych w JSON
    ├── download_log.json           # Log szczegółowy każdego pobrania
    ├── albums_mapping.json         # Mapowanie photo_id -> album(s)
    └── skipped_files.json          # Pliki już na dysku (pominięte)
```

**Nazewnictwo plików:**
- **Zdjęcie W albumie:** `{AlbumName}_{OriginalFilename}`
  - Jeśli w wielu albumach: użyj pierwszego/głównego
  - Przykład: `Wakacje_2023_IMG_001.jpg`
- **Zdjęcie NIE w albumie:** `{OriginalFilename}` lub `{GoogleID}.{ext}`
  - Zachowaj oryginalną nazwę z Google Photos
  - Jeśli Google dostarcza tagi (osoby): można dodać do nazwy (FUTURE)

**Metadane pliku:**
- ✅ Data utworzenia zdjęcia zapisana w EXIF (jeśli zdjęcie)
- ✅ File timestamps (mtime, ctime) ustawione na datę utworzenia
- ✅ Zachowanie oryginalnych metadanych EXIF
- ✅ XMP sidecar (.xmp) z tagami albumów, geolokacją, opisem
  - Kompatybilny z digiKam, Darktable, Lightroom
  - Przenośny - metadane przy pliku

**Działania:**
- Płaski katalog `photos/` (bez hierarchii rok/miesiąc)
- Generowanie nazw z uwzględnieniem albumów
- Obsługa duplikatów nazw (dodaj suffix `_1`, `_2`)
- Zachowanie/ustawienie dat w EXIF i file timestamps
- Utworzenie SQLite database (`photos.db`) z pełnymi metadanymi

---

##### Etap 2.2: Utworzenie Bazy Metadanych
**Cel:** SQLite database z pełnymi metadanymi dla szybkiego wyszukiwania

**Schema SQLite:**
```sql
CREATE TABLE photos (
    id TEXT PRIMARY KEY,              -- Google Photos ID
    filename TEXT NOT NULL,           -- Nazwa pliku na dysku
    original_filename TEXT,           -- Oryginalna nazwa z Google
    mime_type TEXT,
    size_bytes INTEGER,
    width INTEGER,
    height INTEGER,
    creation_time TIMESTAMP,
    upload_time TIMESTAMP,
    latitude REAL,
    longitude REAL,
    description TEXT,
    camera_make TEXT,
    camera_model TEXT,
    downloaded_at TIMESTAMP,
    file_hash TEXT,                   -- SHA256 dla weryfikacji
    marked_for_deletion BOOLEAN DEFAULT 0,  -- Oznaczone do usunięcia (dry-run)
    marked_for_deletion_at TIMESTAMP, -- Kiedy oznaczono
    deleted_from_google BOOLEAN DEFAULT 0,  -- Czy usunięte z Google Photos
    deleted_at TIMESTAMP              -- Kiedy usunięto z Google
);

CREATE TABLE albums (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    photo_count INTEGER,
    cover_photo_id TEXT
);

CREATE TABLE photo_albums (
    photo_id TEXT,
    album_id TEXT,
    PRIMARY KEY (photo_id, album_id),
    FOREIGN KEY (photo_id) REFERENCES photos(id),
    FOREIGN KEY (album_id) REFERENCES albums(id)
);

CREATE INDEX idx_creation_time ON photos(creation_time);
CREATE INDEX idx_location ON photos(latitude, longitude);
CREATE INDEX idx_marked_for_deletion ON photos(marked_for_deletion);
CREATE INDEX idx_deleted_from_google ON photos(deleted_from_google);
```

**Działania:**
- Utworzenie `metadata/photos.db`
- Zapisanie wszystkich metadanych z Google Photos API
- Indeksy dla szybkiego wyszukiwania
- Backup w JSON (`archive_index.json`) dla bezpieczeństwa

---

#### Etap 3: Odczyt Meta Danych z Google

##### Etap 3.1: Pobranie Metadanych Zdjęć
**Cel:** Znalezienie WSZYSTKICH zdjęć w Google Photos + PEŁNE metadane

**Wymaganie:** Pobrać WSZYSTKIE dostępne metadane z Google Photos API (bez wyjątków)

**Działania:**
- Paginacja przez wszystkie media items w Google Photos
- BEZ filtrowania po dacie (bierzemy wszystko)
- Zbieranie WSZYSTKICH metadanych:
  - ID zdjęcia (unikalny)
  - Nazwa pliku
  - Data utworzenia
  - Data dodania do Google Photos
  - Rozmiar (w bajtach)
  - URL do pobrania
  - MIME type
  - Wymiary (width x height)
  - Geolokalizacja (jeśli dostępna)
  - Opis/Caption (jeśli jest)
  - Camera make/model (jeśli dostępne)
  - Wszystkie inne pola z mediaMetadata API

**Output:**
- Lista zdjęć do archiwizacji
- Format: `List[PhotoMetadata]`

---

##### Etap 3.2: Pobranie Albumów
**Cel:** Znalezienie które zdjęcia są w albumach (dla nazewnictwa plików)

**Działania:**
- Pobierz listę wszystkich albumów
- Dla każdego albumu pobierz listę zdjęć (media items)
- Stwórz mapowanie: `photo_id -> album_name(s)`
- Jedno zdjęcie może być w wielu albumach

**Output:**
- Słownik: `{photo_id: [album1, album2, ...]}`

---

##### Etap 3.3: Sprawdzenie Co Już Mamy
**Cel:** Inkrementalna synchronizacja - pomiń już pobrane zdjęcia

**Działania:**
- Wczytaj `metadata/archive_index.json` (jeśli istnieje)
- Porównaj ID/filename/rozmiar z Google Photos
- Stwórz listę NOWYCH zdjęć do pobrania
- Zdjęcia już na dysku = pomijamy (zakładamy że się nie zmieniają)

**Output:**
- Lista zdjęć już na dysku (skip)
- Lista nowych zdjęć do pobrania

---

#### Etap 4: Pobieranie Danych

##### Etap 4.1: Pobieranie Zdjęć
**Cel:** Download zdjęć na lokalny dysk z prawidłowymi metadanami

**Działania:**
- **Przetwarzanie w batchach (50 zdjęć)** - synchronizacja plik↔baza
- Dla każdego batcha 50 zdjęć:
  1. **Operacje na plikach:**
     - Określ nazwę pliku (z albumem lub bez)
     - Pobierz plik z URL
     - Zapisz w `photos/` (płaski katalog)
     - Ustaw file timestamps (mtime/ctime) na datę utworzenia
     - Zweryfikuj/uzupełnij EXIF data (dla zdjęć jpg/png)
     - **Wygeneruj XMP sidecar** z tagami albumów i geolokacją
       - Tagi informacyjne: albumy, geolokalizacja, opisy
       - Tagi procesowe: MARKED_FOR_DELETION, DELETED_FROM_GOOGLE (dodawane później)
     - Zweryfikuj integralność (rozmiar, hash)
  
  2. **Commit do bazy (po zakończeniu batcha):**
     - Zapisz metadane 50 zdjęć do **SQLite (`photos.db`)** - batch INSERT
     - `db.commit()` - transakcja zatwierdzona
     - Zapisz do `metadata/download_log.json` (append batch)
  
  3. **Następny batch:**
     - Kolejne 50 zdjęć → operacje na plikach → commit do bazy
     - Progress bar (tqdm) aktualizowany po każdym batchu

**Bezpieczeństwo synchronizacji:**
- ✅ Stan bazy ZAWSZE odpowiada stanom plików na dysku
- ✅ W razie błędu: baza zawiera tylko faktycznie pobrane pliki
- ✅ Wznowienie (resume): sprawdź bazę, pobierz tylko brakujące

**Obsługa błędów:**
- Retry 3x przy timeout (w ramach batcha)
- Skip przy błędzie i zapisz w error log
- Commit batcha: tylko udane pliki trafiają do bazy
- Możliwość wznowienia (resume) od ostatniego commita

---

##### Etap 4.2: Weryfikacja
**Cel:** Upewnienie się, że wszystko zostało pobrane prawidłowo

**Działania:**
- Porównaj liczbę plików: Google Photos vs lokalny dysk
- Porównaj rozmiary
- Lista zdjęć z błędami (do pobrania ponownie)

**Output:**
- Raport weryfikacji
- Lista OK vs lista błędów

---

#### Etap 5: Oznaczanie Plików do Usunięcia

##### Etap 5a: Kalkulacja Usuwania
**Cel:** Kalkulacja ile miejsca zostanie odzyskane - TYLKO RAPORT

**Kryteria usuwania:**
- ✅ Zdjęcie starsze niż 2 lata (< 2024-01-10)
- ✅ Zdjęcie NIE jest w żadnym albumie
- ✅ Zdjęcie zostało pomyślnie pobrane na dysk

**Działania:**
- Wczytaj `metadata/download_log.json` (co mamy na dysku)
- Pobierz listę wszystkich albumów z Google Photos
- Sprawdź które zdjęcia są w albumach
- Filtruj: starsze niż 2 lata + NIE w albumach + już na dysku
- Kalkuluj rozmiar do usunięcia
- **NIE usuwaj niczego**
- **NIE oznaczaj w bazie**

**Output:**
```
📊 Raport usuwania (kalkulacja):
- Zdjęć na Google (wszystkich): 28,543
- Zdjęć starszych niż 2 lata: 18,234
- Zdjęć w albumach (zachowane): 2,802
- Zdjęć DO USUNIĘCIA: 15,432
  └─ Kryteria: >2 lata + NIE w albumach + już na dysku
- Miejsce do odzyskania: 87.5 GB
- Zakres dat usuwanych: 2020-01-05 do 2024-01-09

⚠️  Następny etap: Etap 5b (oznacza zdjęcia)
```

---

##### Etap 5b: Oznaczenie Zdjęć do Usunięcia
**Cel:** Oznaczenie zdjęć w bazie + XMP sidecars + OPCJONALNIE w Google Photos

**Działania:**
- Powtórz filtrowanie (jak w Etap 5a)
- **Przetwarzanie w batchach (50 zdjęć)** - synchronizacja XMP↔baza
- Dla każdego batcha:
  1. **Operacje na plikach XMP:**
     - Dla każdego z 50 zdjęć: dodaj tag "MARKED_FOR_DELETION" do XMP sidecar
     - Weryfikuj że XMP zapisany prawidłowo
  
  2. **Commit do bazy (po zakończeniu batcha):**
     - `UPDATE photos SET marked_for_deletion = 1, marked_for_deletion_at = NOW() WHERE id IN (batch_50_ids)`
     - `db.commit()` - transakcja zatwierdzona
  
  3. **OPCJONALNIE: Tag w Google Photos** (po commitcie do bazy):
     - Dodaj tag w Google Photos "MARKED_FOR_DELETION" dla batcha 50 zdjęć
     - Wymaga Google Photos API (mutating operations)
     - Dodatkowe bezpieczeństwo wizualne

- Zapisz listę do `metadata/marked_for_deletion.json` (append po każdym batchu)
- Raport ile zdjęć oznaczono (aktualizowany po każdym batchu)

**Output:**
```
✅ Oznaczono zdjęcia do usunięcia:
- Zdjęć oznaczonych w bazie: 15,432
- Zdjęć otagowanych w Google Photos: 15,432 (opcjonalne)
- Lista zapisana w: metadata/marked_for_deletion.json

⚠️  Sprawdź listę, zweryfikuj w Google Photos (tag: MARKED_FOR_DELETION)
⚠️  Następny krok: python delete_from_google.py (NIEODWRACALNE usunięcie)
```

**Bezpieczeństwo:**
- ✅ Możesz przejrzeć oznaczone zdjęcia w Google Photos (filtr: tag "MARKED_FOR_DELETION")
- ✅ Możesz anulować - usunąć tag i flagi w bazie przed faktycznym usunięciem
- ✅ Lista w JSON do manualnej weryfikacji
---

### Proces 2: Usuwanie Flagi (OPCJONALNY)
**Komenda:** `python clear_marks.py`

**Opis:** Czyszczenie oznaczeń marked_for_deletion - anulowanie Etapu 5 z Procesu Głównego

**Wykonywany:** Niezależnie, pomija Etapy 1-5
**Cel:** Usunięcie oznaczeń `marked_for_deletion` - anulowanie Etapu 5

**Kiedy użyć:**
- ❌ Coś się rozjechało z oznaczaniem
- ❌ Zmieniłeś zdanie
- ❌ Pomyłka w kryteriach
- ❌ Chcesz ponownie uruchomić Etap 5 z innymi parametrami

**Działania:**
- Query: `UPDATE photos SET marked_for_deletion = 0, marked_for_deletion_at = NULL WHERE marked_for_deletion = 1`
- **OPCJONALNIE:** Usuń tagi "MARKED_FOR_DELETION" z Google Photos
- Usuń plik `metadata/marked_for_deletion.json`
- Raport: ile flag wyczyszczono

**Output:**
```
🧹 Czyszczenie oznaczeń do usunięcia:
- Zdjęć z flagą marked_for_deletion: 15,432
- Flagi wyczyszczone: 15,432
- Tagi usunięte z Google Photos: 15,432 (opcjonalnie)
- Plik marked_for_deletion.json usunięty

✅ Możesz teraz ponownie uruchomić Etap 5b z Procesu Głównego
```

**Bezpieczeństwo:**
- ✅ NIE dotyka zdjęć już usuniętych (`deleted_from_google = 1` pozostaje)
- ✅ Bezpieczne - tylko czyści flagi, nie usuwa plików
- ✅ Można używać wielokrotnie
---

### Proces 3: Usuwanie z Google Photos (OPCJONALNY)
**Komenda:** `python delete_from_google.py`

**Opis:** Usunięcie zdjęć z Google Photos (tylko te z flagą marked_for_deletion = 1)

**Wykonywany:** Niezależnie, pomija Etapy 1-5
**Cel:** Usunięcie zdjęć z Google Photos

**Wymagania przed uruchomieniem:**
- ✅ Etap 5b wykonany (`marked_for_deletion = 1` w bazie)
- ✅ Lista `metadata/marked_for_deletion.json` istnieje
- ✅ Użytkownik zweryfikował listę (opcjonalnie w Google Photos przez tag)

**Kluczowa zasada:**
- **Usuwamy TYLKO zdjęcia z flagą `marked_for_deletion = 1`**
- **NIE sprawdzamy ponownie kryteriów** (wiek, albumy itp.)
- **Ufamy flagom w bazie** - to co zostało oznaczone w Etapie 5

**Działania:**
1. **Weryfikacja:**
   - Query: `SELECT * FROM photos WHERE marked_for_deletion = 1 AND deleted_from_google = 0`
   - Sprawdź czy pliki nadal na dysku i hash się zgadza (bezpieczeństwo)
   - **SPRAWDŹ XMP sidecars:** Czy tag "MARKED_FOR_DELETION" nadal istnieje?
     - Jeśli użytkownik usunął tag w digiKam → POMIŃ to zdjęcie (ochrona!)
     - Jeśli tag istnieje → OK do usunięcia
   - Lista zdjęć do usunięcia = **tylko te z flagą + tag w XMP**

2. **Usunięcie z Google Photos API (batch po batch):**
   - **Przetwarzanie w batchach (50 zdjęć)** - synchronizacja Google↔XMP↔baza
   - Dla każdego batcha:
     
     a) **Usunięcie z Google Photos:**
        - Batch delete: 50 zdjęć na request
        - Delay między requestami (rate limiting)
        - Log każdego usunięcia
        - Jeśli błąd w batchu: retry całego batcha 3x
        - Jeśli nadal błąd: POMIŃ batch, zapisz do error log, NIE aktualizuj bazy
     
     b) **Operacje na XMP sidecars (tylko dla udanych):**
        - Dla każdego usuniętego z Google: dodaj tag "DELETED_FROM_GOOGLE" do XMP
        - Informacja widoczna w digiKam (read-only)
        - Użytkownik widzi które zdjęcia już nie ma w Google Photos
     
     c) **Commit do bazy (po zakończeniu batcha):**
        - `UPDATE photos SET deleted_from_google = 1, deleted_at = NOW() WHERE id IN (batch_50_ids)`
        - Zostaw `marked_for_deletion = 1` (historia)
        - `db.commit()` - transakcja zatwierdzona
        - Zapisz batch do `metadata/deleted_photos.json` (append)

3. **Synchronizacja zapewniona:**
   - ✅ Google Photos usunięte → XMP zaktualizowane → baza zaktualizowana
   - ✅ W razie błędu: baza zawiera tylko faktycznie usunięte z Google
   - ✅ Możliwość retry: sprawdź bazę, usuń tylko te z `deleted_from_google = 0`

4. **Opcjonalnie: Usunięcie tagów**
   - Jeśli były tagi "MARKED_FOR_DELETION" - zdjęcia już nie istnieją, więc tagi znikną automatycznie

**Backup i rollback:**
- Lista usuniętych w `metadata/deleted_photos.json`
- Google Photos Trash: 60 dni na odzyskanie
- Można przywracać z kosza (batch restore API)

---

## Statystyki i Raportowanie

### Raport Kalkulacji
```json
{
  "mode": "calculation",
  "date": "2026-01-10T20:53:00Z",
  "cutoff_date": null,
  
  "photos": {
    "total_in_google": 28543,
    "already_on_disk": 13111,
    "new_to_download": 15432,
    "total_size_gb": 87.5,
    "breakdown_by_year": {
      "2022": {"count": 5234, "size_gb": 28.3},
      "2023": {"count": 10198, "size_gb": 59.2}
    },
    "breakdown_by_type": {
      "images": {"count": 14001, "size_gb": 65.3},
      "videos": {"count": 1431, "size_gb": 22.2}
    }
  },
  
  "archive": {
    "destination": "/mnt/data/google-archiver",
    "available_space_gb": 870,
    "required_space_gb": 87.5,
    "sufficient_space": true
  },
  
  "estimated_time": {
    "download_hours": 2.4,
    "total_hours": 3.0
  },
  
  "google_photos": {
    "space_to_reclaim_gb": 87.5,
    "percentage_of_quota": "58%"
  }
}
```

---

## Kolejność Wykonania

### Proces Główny: Backup i Przygotowanie do Usuwania (DEFAULT)
```bash
python main.py  # Bezpieczna operacja - backup + oznaczanie plików
```

**Kolejność etapów:**
1. ✅ **Etap 1:** Uwierzytelnienie
2. ✅ **Etap 2:** Utworzenie struktury folderów i bazy (jednorazowo)
3. ✅ **Etap 3:** Pobranie metadanych WSZYSTKICH zdjęć i albumów z Google
4. ✅ **Etap 3:** Porównanie z tym co już jest na dysku (inkrementalne)
5. ✅ **Etap 4:** Pobieranie nowych zdjęć (z progress bar)
6. ✅ **Etap 4:** Weryfikacja
7. ✅ **Etap 5:** Kalkulacja i oznaczanie plików do usunięcia
8. ✅ Raport końcowy

### Usuwanie Flagi (OPCJONALNY)
```bash
# Wykonywane NIEZALEŻNIE - pomija etapy 1-5
python clear_marks.py
# Czyści wszystkie flagi marked_for_deletion w bazie i XMP
```

**Kiedy użyć:**
- Chcesz anulować oznaczenia do usunięcia
- Pomyłka w kryteriach podczas Etapu 5
- Chcesz ponownie uruchomić Etap 5 z innymi parametrami

---

### Usuwanie z Google Photos (OPCJONALNY)
```bash
# Wykonywane NIEZALEŻNIE - pomija etapy 1-5
python delete_from_google.py
# Usuwa z Google Photos tylko zdjęcia z flagą marked_for_deletion = 1
# Google Photos ma kosz (60 dni) - można odzyskać jeśli błąd
```

**Wymagania:**
- Etap 5 musi być wcześniej wykonany (pliki oznaczone `marked_for_deletion = 1`)
- Lista `metadata/marked_for_deletion.json` musi istnieć

---

## Parametry Konfiguracyjne

### `.env`
```bash
# Archiwizacja
ARCHIVE_PATH=/mnt/data/google-archiver
INCREMENTAL=true  # Pomijaj już pobrane zdjęcia

# Download settings
DOWNLOAD_THREADS=5
RETRY_COUNT=3
DOWNLOAD_BATCH_SIZE=100

# Google API
PHOTOS_API_BATCH_SIZE=100
RATE_LIMIT_DELAY_MS=100
```

---

## Bezpieczeństwo

### Checklist przed usunięciem z Google:
- [ ] Wszystkie zdjęcia pobrane
- [ ] Weryfikacja integralności (100% OK)
- [ ] Backup na drugim dysku/chmurze (opcjonalnie)
- [ ] Test odzyskiwania kilku losowych zdjęć
- [ ] Export metadanych zakończony
- [ ] Użytkownik potwierdził (manual check)

---

## Metryki Sukcesu

### Backup/Download:
- ✅ Prawidłowa liczba WSZYSTKICH zdjęć
- ✅ Poprawne wykrycie już pobranych (pomijanie duplikatów)
- ✅ 100% zdjęć pobranych (nowych)
- ✅ 0% błędów integralności
- ✅ Struktura folderów prawidłowa
- ✅ Metadata zapisana kompletnie
- ✅ Suma rozmiarów zgadza się z Google Photos

### Delete (kalkulacja i rzeczywiste usuwanie):
- ✅ Miejsce odzyskane na Google Photos
- ✅ Zdjęcia nadal dostępne lokalnie
- ✅ Log wszystkich usuniętych plików
