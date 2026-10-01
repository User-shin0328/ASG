import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from evaluation.scan_image_archive import scan_archive


class ImageArchiveScanTests(unittest.TestCase):
    def archive_with(self, content: bytes) -> Path:
        temp = tempfile.NamedTemporaryFile(suffix=".tar", delete=False)
        temp.close()
        path = Path(temp.name)
        info = tarfile.TarInfo("etc/example.conf")
        info.size = len(content)
        with tarfile.open(path, "w") as archive:
            archive.addfile(info, io.BytesIO(content))
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_scans_all_regular_files_without_printing_secret_material(self):
        marker = b"sk-proj-" + b"A" * 30
        findings = scan_archive(self.archive_with(b"config=" + marker))
        self.assertEqual(findings, [("etc/example.conf", "provider-token")])
        self.assertNotIn(marker.decode(), repr(findings))

    def test_clean_image_file_has_no_finding(self):
        self.assertEqual(scan_archive(self.archive_with(b"ordinary configuration")), [])


if __name__ == "__main__":
    unittest.main()
