#!/usr/bin/env python
"""
Preview template notifikasi WhatsApp yang baru.
"""
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.adapters.notification import build_review_message


def main():
    print("=" * 70)
    print("Preview Template Notifikasi WhatsApp")
    print("=" * 70)
    print()
    
    # Test dengan berbagai variasi
    test_cases = [
        {
            "article_id": 1,
            "title": "Kegiatan Ekstrakurikuler Robotik Juara 1 Tingkat Nasional",
            "timestamp": datetime(2026, 7, 13, 14, 30, tzinfo=UTC),
            "instagram_username": "smkn1jakarta",
            "category": "Prestasi",
        },
        {
            "article_id": 2,
            "title": "Tips Sukses Menghadapi Ujian Semester: Strategi Belajar Efektif",
            "timestamp": datetime(2026, 7, 13, 10, 15, tzinfo=UTC),
            "instagram_username": "smkn1jakarta",
            "category": "Edukasi",
        },
        {
            "article_id": 3,
            "title": "Penerimaan Siswa Baru 2026: Panduan Lengkap dan Jadwal Penting",
            "timestamp": None,  # Test tanpa timestamp
            "instagram_username": None,  # Test tanpa username
            "category": "Pengumuman",
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}:")
        print("-" * 70)
        
        message = build_review_message(**test_case)
        print(message)
        
        print()
        print("=" * 70)
        print()
    
    print("✨ Preview selesai! Template siap digunakan.")


if __name__ == "__main__":
    main()
