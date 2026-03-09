// Turkish locale strings and shared label maps for Koç Büro Tender Dashboard

export const TR = {
  // Navigation
  nav: {
    overview: 'Karar Masası',
    tenders: 'İhaleler',
    suppressed: 'Arşiv & Red',
    reports: 'Raporlar',
    health: 'Çalışma Durumu',
  },

  // Sidebar
  sidebar: {
    brand: 'KOÇ BÜRO',
    subtitle: 'İhale Radarı',
    lastScan: 'Son tarama:',
    autoRefresh: 'Otomatik yenileme aktif',
  },

  // Common
  loading: 'Gösterge paneli yükleniyor…',
  loadingReports: 'Raporlar yükleniyor…',
  loadingContent: 'Rapor içeriği yükleniyor…',
  loadingHistory: 'Geçmiş yükleniyor…',

  // Overview / Decision Desk
  overview: {
    title: 'Karar Masası',
    lastScan: 'Son tarama',
    unknown: 'bilinmiyor',
    status: 'Durum:',
    scanTime: 'Tarama zamanı:',
    topCandidates: 'Öne Çıkan Adaylar',
    candidateCount: (n) => n > 0 ? `${n} ihale incelemeye değer` : 'Aday bulunamadı',
    emptyCandidates: 'Mevcut taramada aksiyon veya güçlü aday ihalesi bulunamadı.',
    // Decision queue copy
    queueTitle: 'Dikkat Gerektiren',
    queueSubtitle: 'Operatör kararı bekleyen ihaleler',
    queueEmpty: 'Şu an bekleyen karar yok — tüm ihaleler işlenmiş.',
    sectionCritical: 'Acil',
    sectionAction: 'Aksiyon Gerekli',
    sectionWatch: 'Takipte',
    statsCompact: 'Tarama Özeti',
    deadlineToday: 'Bugün',
    deadlineTomorrow: 'Yarın',
    deadlineDays: (n) => `${n} gün`,
    deadlinePassed: 'Geçti',
    newBadge: 'Yeni',
    pendingDecision: 'Karar bekliyor',
  },

  // Stats
  stats: {
    scanned: 'Taranan',
    unique: 'Benzersiz',
    action: 'Aksiyon',
    strong_candidate: 'Güçlü Aday',
    watch: 'Takip',
    silent_reject: 'Sessiz Red',
    hard_rejected: 'Kesin Red',
    suppressed: 'Baskılanan',
  },

  // Tender Table
  tenderTable: {
    title: 'Tüm İhaleler',
    showing: (shown, total) => `${total} ihaleden ${shown} tanesi gösteriliyor`,
    searchPlaceholder: 'Başlık, kurum, IKN veya il ara…',
    allClassifications: 'Tüm sınıflar',
    allStatuses: 'Tüm durumlar',
    allProvinces: 'Tüm iller',
    noMatch: 'Filtrelerinize uygun ihale bulunamadı.',
    footerShowing: (n) => `${n} ihale gösteriliyor`,
    footerSort: (key, dir) => `${SORT_KEY_LABELS[key] || key} (${dir === 'asc' ? 'artan' : 'azalan'})`,
    exportCsv: 'Dışa Aktar',
  },

  // Table headers
  th: {
    score: 'Puan',
    classification: 'Sınıf',
    status: 'Durum',
    province: 'İl',
    authority: 'Kurum',
    title: 'Başlık',
    deadline: 'Son Tarih',
    confidence: 'Güven',
    urgency: 'Aciliyet',
    label: 'Etiket',
    ikn: 'IKN',
    reason: 'Sebep',
    time: 'Zaman',
    event: 'Olay',
    summary: 'Özet',
  },

  // Tender Detail
  detail: {
    reportedToday: 'Bugün raporlandı',
    sectionInfo: 'Bilgiler',
    sectionScore: 'Puan Detayı',
    sectionRisk: 'Risk İşaretleri',
    sectionKeywords: 'Eşleşen Anahtar Kelimeler',
    sectionClusters: 'Eşleşen Kümeler',
    sectionNotes: 'Sistem Notları',
    sectionActions: 'Operatör İşlemleri',
    labelIkn: 'IKN',
    labelProvince: 'İl',
    labelAuthority: 'Kurum',
    labelDeadline: 'Son Tarih',
    labelScore: 'Puan',
    labelConfidence: 'Güven',
    noReasons: 'Puanlama gerekçesi bulunamadı.',
    manualLabel: 'Manuel Etiket',
    operatorNotes: 'Operatör Notları',
    notesPlaceholder: 'Bu ihale hakkında not ekleyin…',
    save: 'Kaydet',
    saving: 'Kaydediliyor…',
  },

  // Archive & Rejected View (was: Suppressed View)
  suppressed: {
    title: 'Arşiv & Reddedilen',
    subtitle: 'Sistem tarafından elenen veya arşivlenen ihaleler',
    tabSuppressed: (n) => `Arşiv (${n})`,
    tabHardRejected: (n) => `Kesin Red (${n})`,
    tabSilentRejected: (n) => `Sessiz Red (${n})`,
    searchPlaceholder: 'Ara…',
    noItems: 'Bu kategoride kayıt bulunamadı.',
    itemCount: (n) => `${n} kayıt`,
    reasonRejected: 'Filtre kurallarına göre reddedildi',
    reasonOutOfWindow: 'Son tarih geçti veya tarama penceresi dışında',
    reasonSuppressed: (count) => `${count}x tekrar — tekilleştirme ile arşivlendi`,
    // Section descriptions
    archiveDesc: 'Tekrar eden veya süresi geçen ihaleler. Otomatik olarak arşivlendi.',
    hardRejectDesc: 'Puanlama kurallarına göre kesin olarak elenen ihaleler.',
    silentRejectDesc: 'Eşik altı kalan, sessizce elenen ihaleler.',
  },

  // Reports
  reports: {
    title: 'Raporlar',
    count: (n) => `${n} rapor mevcut`,
    noReports: 'Rapor bulunamadı.',
    failedLoad: 'Rapor yüklenemedi.',
  },

  // Run Health
  health: {
    title: 'Çalışma Durumu',
    subtitle: 'Sistem durumu ve son aktivite',
    stale: 'Tarama güncel olmayabilir',
    healthy: 'Sistem sağlıklı',
    lastRunType: 'Son Çalışma Tipi',
    lastDailyScan: 'Son Günlük Tarama',
    lastDeltaScan: 'Son Delta Tarama',
    lastWeeklySummary: 'Son Haftalık Özet',
    lastSuccess: 'Son Başarılı',
    updatedAt: 'Güncelleme Zamanı',
    lastScanCounts: 'Son Tarama Sayıları',
    reportPaths: 'Rapor Dosya Yolları',
    lastReport: 'Son rapor:',
    lastWeekly: 'Son haftalık:',
    eventLog: 'Olay Günlüğü',
    events: (n) => `${n} olay`,
    noHistory: 'Geçmiş olayı bulunamadı.',
    showingEvents: (shown, total) => `${total} olaydan ${shown} tanesi gösteriliyor`,
  },

  // Bid Tracking
  bidTracking: {
    title: 'Teklif Takibi',
    status: 'Teklif Durumu',
    bidAmount: 'Teklif Tutarı',
    bidDate: 'Teklif Tarihi',
    resultDate: 'Sonuç Tarihi',
    notes: 'Notlar',
    lossReason: 'Kaybetme Sebebi',
    noTracking: 'Bu ihale için teklif kaydı yok.',
    startTracking: 'Teklif Takibi Başlat',
  },

  // EKAP
  ekap: {
    openSearch: 'EKAP\'ta Ara',
    iknCopied: 'IKN panoya kopyalandı',
  },

  // Toast
  toast: {
    updated: 'İhale güncellendi',
    updateFailed: (msg) => `Güncelleme başarısız: ${msg}`,
  },

  // Age strings
  age: {
    minutes: (n) => `${n}dk önce`,
    hours: (n) => `${n}sa önce`,
    days: (n) => `${n}g önce`,
  },
};

// Sort key display labels
const SORT_KEY_LABELS = {
  external_score: 'Puan',
  internal_score: 'İç Puan',
  classification: 'Sınıf',
  status_tag: 'Durum',
  province: 'İl',
  title: 'Başlık',
  deadline: 'Son Tarih',
  confidence: 'Güven',
  urgency: 'Aciliyet',
};

// Classification display labels (Turkish)
export const CLASS_LABELS = {
  ACTION: 'Aksiyon',
  STRONG_CANDIDATE: 'Güçlü Aday',
  WATCH: 'Takip',
  SILENT_REJECT: 'Sessiz Red',
  HARD_REJECT: 'Kesin Red',
};

// Classification → chip CSS class
export const CLASS_CHIP_MAP = {
  ACTION: 'chip-action',
  STRONG_CANDIDATE: 'chip-strong',
  WATCH: 'chip-watch',
  SILENT_REJECT: 'chip-silent',
  HARD_REJECT: 'chip-hard-reject',
};

// Urgency display labels (Turkish)
export const URGENCY_LABELS = {
  CRITICAL: 'Kritik',
  NORMAL: 'Normal',
  LOW: 'Düşük',
};

// Urgency → chip CSS class
export const URGENCY_CHIP_MAP = {
  CRITICAL: 'chip-critical',
  NORMAL: 'chip-normal',
  LOW: 'chip-low',
};

// Operator label display names (Turkish)
export const OPERATOR_LABEL_NAMES = {
  none: 'Yok',
  priority: 'Öncelik',
  watch: 'Takip',
  reject: 'Red',
  never_show_similar: 'Benzerini Gösterme',
};

// Status labels for suppressed view
export const STATUS_LABELS = {
  REJECTED: 'Reddedildi',
  OUT_OF_WINDOW: 'Süresi Geçmiş',
  SEEN: 'Görüldü',
  HARD_REJECT: 'Kesin Red',
  SILENT_REJECT: 'Sessiz Red',
};

// Bid status display labels (Turkish)
export const BID_STATUS_LABELS = {
  reviewing: 'İnceleniyor',
  preparing_bid: 'Teklif Hazırlanıyor',
  bid_submitted: 'Teklif Verildi',
  won: 'Kazanıldı',
  lost: 'Kaybedildi',
  cancelled: 'İptal',
  no_bid: 'Teklif Verilmedi',
};

// Bid status → chip CSS class
export const BID_STATUS_CHIPS = {
  reviewing: 'chip-watch',
  preparing_bid: 'chip-strong',
  bid_submitted: 'chip-action',
  won: 'chip-action',
  lost: 'chip-hard-reject',
  cancelled: 'chip-silent',
  no_bid: 'chip-silent',
};

// Scan count key labels
export const COUNT_KEY_LABELS = {
  scanned: 'Taranan',
  unique: 'Benzersiz',
  action: 'Aksiyon',
  strong_candidate: 'Güçlü Aday',
  watch: 'Takip',
  silent_reject: 'Sessiz Red',
  hard_rejected: 'Kesin Red',
  suppressed: 'Baskılanan',
};

// Shared helper: format date/time in Turkish locale
export function formatDateTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('tr-TR') + ' ' + d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
}

export function formatTime(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return iso;
  }
}

export function getAgeString(iso) {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 60) return TR.age.minutes(mins);
  const hours = Math.floor(mins / 60);
  if (hours < 24) return TR.age.hours(hours);
  const days = Math.floor(hours / 24);
  return TR.age.days(days);
}

export function scoreClass(score) {
  if (score == null) return 'score-low';
  if (score >= 6) return 'score-high';
  if (score >= 3) return 'score-mid';
  return 'score-low';
}

export function parseDeadline(str) {
  if (!str) return 0;
  const m = str.match(/(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})/);
  if (!m) return 0;
  return new Date(+m[3], +m[2] - 1, +m[1], +m[4], +m[5]).getTime();
}

export function getDeadlineLabel(str) {
  const ts = parseDeadline(str);
  if (!ts) return null;
  const now = Date.now();
  const diff = ts - now;
  if (diff < 0) return TR.overview.deadlinePassed;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return TR.overview.deadlineToday;
  if (days === 1) return TR.overview.deadlineTomorrow;
  return TR.overview.deadlineDays(days);
}

export function openEkap(ikn) {
  if (ikn) {
    navigator.clipboard.writeText(ikn).catch(() => {});
  }
  window.open('https://ekap.kik.gov.tr/EKAP/Ortak/IhaleArama/index.html', '_blank');
}
