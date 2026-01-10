# Google Archiver

Automatyczna archiwizacja danych z Google (Photos, Drive, Gmail) na lokalny dysk.

## Cel - Faza 1: Zdjęcia
Zwolnienie miejsca na Google Photos poprzez przeniesienie zdjęć starszych niż 2 lata, które NIE są w żadnych albumach.

## Architektura
- **Źródło**: Google Photos API
- **Cel**: `/mnt/data/google-photos-archive/` (916GB Kubernetes PV)
- **Tryb**: Dry-run (tylko listowanie) → Backup → Weryfikacja → Usunięcie

## Status
🚧 W budowie - dry-run only
