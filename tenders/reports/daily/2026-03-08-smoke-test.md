# Koç Büro Tender Radar — Smoke Test

Date: 2026-03-08
Run type: manual calibration / pre-cron smoke test

## Tested queries
- mobilya
- büro mobilya
- ofis mobilya
- tefrişat
- mefruşat
- masa sandalye koltuk
- hastane mobilya
- otel mobilya
- konferans mobilya
- okul mobilya

## Raw results
- Total raw hits across tested queries: 51
- Unique tenders after IKN dedupe: 38

## Immediate findings
1. `mobilya` is high-recall but very noisy.
2. `mefruşat` is especially noisy and pulls many textile / cleaning / mixed-supply tenders.
3. `ofis mobilya` and `büro mobilya` produce far cleaner results.
4. `tefrişat` can surface relevant opportunities, but requires detail review.
5. Segment queries like `hastane mobilya`, `otel mobilya`, and `konferans mobilya` produced low direct yield in this sample.

## Strong sample candidates found
- 2026/251282 — Payas Stem Yapay Zeka Merkezi Ofis Mobilyaları
- 2026/338946 — Gençlik Merkezi Mobilya (Montaj Dahil)
- 2026/356152 — Van İli Muradiye İlçesi Kültür Merkezi Tefrişat Malzemesi Alım İşi
- 2026/373823 — Esenyurt Belediyesi Sosyal Tesisleri Mobilya Alımı İşi

## Noise patterns observed
- park / kent mobilyası / oyun ekipmanları
- temizlik malzemesi
- kırtasiye + mefruşat karma alımları
- bilişim / sunucu / bilgisayar
- beyaz eşya / endüstriyel mutfak
- inşaat / marangoz atölyesi malzemeleri

## Tuning actions applied after smoke test
- hard reject list expanded with:
  - kent donatı
  - kent donatı elemanları
  - oyun ekipmanları
  - çöp kovası
- soft reject list expanded with:
  - kırtasiye
  - beyaz eşya
  - endüstriyel mutfak
  - cerrahi el aletleri
  - bilişim malzemesi
  - profil demir
- broad institutional furniture cluster weight reduced from 0.70 to 0.45
- search config aligned to actual MCP tender type usage (`tender_types: [1]`)

## Conclusion
System scaffold is viable. Precision will depend on keeping broad terms heavily filtered and leaning more on office-specific keywords plus detail enrichment for tefrişat-style results.
