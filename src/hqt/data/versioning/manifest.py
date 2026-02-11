"""
Data manifest generation and verification for HQT Trading System.

This module provides manifest.json generation and verification to track
all data versions and enable integrity checking.

[REQ: DAT-FR-028] Preserve previous versions
[SDD: §5.2] Data Storage Architecture
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from hqt.data.storage.catalog import DataCatalog
from hqt.data.versioning.hasher import verify_file_hash


class DataManifest:
    """
    Data manifest generation and verification.

    Generates manifest.json containing all data file hashes and metadata,
    enabling integrity verification and version tracking.

    Manifest Format:
        ```json
        {
            "generated_at": "2024-01-15T10:30:00Z",
            "hqt_version": "1.0.0",
            "total_files": 42,
            "total_size_bytes": 1234567890,
            "files": [
                {
                    "symbol": "EURUSD",
                    "timeframe": "H1",
                    "partition": "2024",
                    "file_path": "data/parquet/EURUSD/H1/2024.parquet",
                    "version_hash": "abc123...",
                    "row_count": 8760,
                    "min_timestamp": 1704067200000000,
                    "max_timestamp": 1735689599000000,
                    "file_size_bytes": 524288,
                    "data_source": "mt5"
                }
            ]
        }
        ```

    Example:
        ```python
        from hqt.data.versioning import DataManifest
        from hqt.data.storage import DataCatalog

        catalog = DataCatalog("data/catalog.db")
        manifest = DataManifest(catalog)

        # Generate manifest
        result = manifest.generate("data/manifest.json")
        print(f"Generated manifest with {result['total_files']} files")

        # Later, verify data integrity
        verification = manifest.verify("data/manifest.json")
        if verification["valid"]:
            print("✓ All data files verified")
        else:
            print(f"✗ {len(verification['issues'])} issues found")
        ```
    """

    def __init__(self, catalog: DataCatalog):
        """
        Initialize manifest generator.

        Args:
            catalog: Data catalog to read metadata from
        """
        self.catalog = catalog

    def generate(
        self,
        output_path: str | Path,
        hqt_version: str = "1.0.0",
    ) -> dict[str, Any]:
        """
        Generate data manifest file.

        Args:
            output_path: Path to write manifest.json
            hqt_version: HQT system version

        Returns:
            Dictionary with generation results:
                - manifest_path: Path to manifest file
                - total_files: Number of files in manifest
                - total_size_bytes: Total size of all files

        Example:
            ```python
            result = manifest.generate("data/manifest.json")
            print(f"Manifest: {result['manifest_path']}")
            print(f"Files: {result['total_files']}")
            print(f"Total size: {result['total_size_bytes'] / 1024 / 1024:.1f} MB")
            ```
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get all catalog entries
        entries = self.catalog.query_available()

        # Build manifest
        files = []
        total_size = 0

        for entry in entries:
            file_info = {
                "symbol": entry["symbol"],
                "timeframe": entry["timeframe"],
                "partition": entry["partition"],
                "file_path": entry["file_path"],
                "version_hash": entry["version_hash"],
                "row_count": entry["row_count"],
                "min_timestamp": entry["min_timestamp"],
                "max_timestamp": entry["max_timestamp"],
                "file_size_bytes": entry["file_size_bytes"],
                "data_source": entry["data_source"],
            }
            files.append(file_info)
            total_size += entry["file_size_bytes"] if entry["file_size_bytes"] else 0

        manifest = {
            "generated_at": datetime.now().isoformat(),
            "hqt_version": hqt_version,
            "total_files": len(files),
            "total_size_bytes": total_size,
            "files": files,
        }

        # Write manifest
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return {
            "manifest_path": str(output_path),
            "total_files": len(files),
            "total_size_bytes": total_size,
        }

    def verify(
        self,
        manifest_path: str | Path,
        check_hashes: bool = True,
    ) -> dict[str, Any]:
        """
        Verify data against manifest.

        Checks that:
        1. All files in manifest exist
        2. File hashes match (if check_hashes=True)

        Args:
            manifest_path: Path to manifest.json
            check_hashes: Verify file hashes (slow for many files)

        Returns:
            Dictionary with verification results:
                - valid: bool - True if all checks pass
                - issues: list[str] - Issues found
                - verified_files: int - Number of files verified
                - total_files: int - Total files in manifest
                - manifest_generated_at: ISO timestamp

        Example:
            ```python
            result = manifest.verify("data/manifest.json")

            if result["valid"]:
                print(f"✓ All {result['total_files']} files verified")
            else:
                print(f"✗ Verification failed:")
                for issue in result["issues"]:
                    print(f"  - {issue}")
            ```
        """
        manifest_path = Path(manifest_path)

        if not manifest_path.exists():
            return {
                "valid": False,
                "issues": [f"Manifest not found: {manifest_path}"],
                "verified_files": 0,
                "total_files": 0,
                "manifest_generated_at": None,
            }

        # Load manifest
        with open(manifest_path) as f:
            manifest = json.load(f)

        files = manifest.get("files", [])
        issues = []
        verified_files = 0

        for file_info in files:
            file_path = Path(file_info["file_path"])

            # Check file exists
            if not file_path.exists():
                issues.append(
                    f"Missing file: {file_path} "
                    f"({file_info['symbol']} {file_info['timeframe']} {file_info['partition']})"
                )
                continue

            # Verify hash
            if check_hashes and file_info.get("version_hash"):
                try:
                    if not verify_file_hash(file_path, file_info["version_hash"]):
                        issues.append(
                            f"Hash mismatch: {file_path} "
                            f"({file_info['symbol']} {file_info['timeframe']} {file_info['partition']}) "
                            f"- file has been modified"
                        )
                        continue
                except Exception as e:
                    issues.append(
                        f"Hash verification failed: {file_path} - {e}"
                    )
                    continue

            verified_files += 1

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "verified_files": verified_files,
            "total_files": len(files),
            "manifest_generated_at": manifest.get("generated_at"),
        }

    def update(
        self,
        manifest_path: str | Path,
        hqt_version: str = "1.0.0",
    ) -> dict[str, Any]:
        """
        Update existing manifest with new files.

        Preserves existing entries and adds new ones from catalog.
        Does NOT remove entries for deleted files.

        Args:
            manifest_path: Path to manifest.json
            hqt_version: HQT system version

        Returns:
            Dictionary with update results:
                - added: int - Number of files added
                - updated: int - Number of files updated
                - total_files: int - Total files in manifest

        Example:
            ```python
            # After downloading new data
            result = manifest.update("data/manifest.json")
            print(f"Added {result['added']} new files")
            print(f"Updated {result['updated']} existing files")
            ```

        Note:
            This is an incremental update. To regenerate from scratch,
            use generate() instead.
        """
        manifest_path = Path(manifest_path)

        # Load existing manifest if it exists
        if manifest_path.exists():
            with open(manifest_path) as f:
                existing_manifest = json.load(f)
            existing_files = {
                (f["symbol"], f.get("timeframe"), f["partition"]): f
                for f in existing_manifest.get("files", [])
            }
        else:
            existing_files = {}

        # Get current catalog entries
        catalog_entries = self.catalog.query_available()

        added = 0
        updated = 0
        files = []
        total_size = 0

        for entry in catalog_entries:
            key = (entry["symbol"], entry["timeframe"], entry["partition"])

            file_info = {
                "symbol": entry["symbol"],
                "timeframe": entry["timeframe"],
                "partition": entry["partition"],
                "file_path": entry["file_path"],
                "version_hash": entry["version_hash"],
                "row_count": entry["row_count"],
                "min_timestamp": entry["min_timestamp"],
                "max_timestamp": entry["max_timestamp"],
                "file_size_bytes": entry["file_size_bytes"],
                "data_source": entry["data_source"],
            }

            if key in existing_files:
                # Check if hash changed
                if existing_files[key].get("version_hash") != entry["version_hash"]:
                    updated += 1
            else:
                added += 1

            files.append(file_info)
            total_size += entry["file_size_bytes"] if entry["file_size_bytes"] else 0

        # Also include files from existing manifest not in catalog
        # (preserves history even if files deleted)
        for key, file_info in existing_files.items():
            if key not in [(f["symbol"], f.get("timeframe"), f["partition"]) for f in files]:
                files.append(file_info)

        # Write updated manifest
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "hqt_version": hqt_version,
            "total_files": len(files),
            "total_size_bytes": total_size,
            "files": files,
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return {
            "added": added,
            "updated": updated,
            "total_files": len(files),
        }

    def diff(
        self,
        manifest1_path: str | Path,
        manifest2_path: str | Path,
    ) -> dict[str, Any]:
        """
        Compare two manifests and show differences.

        Args:
            manifest1_path: Path to first manifest
            manifest2_path: Path to second manifest

        Returns:
            Dictionary with differences:
                - added: list - Files in manifest2 not in manifest1
                - removed: list - Files in manifest1 not in manifest2
                - modified: list - Files with different hashes
                - unchanged: int - Number of unchanged files

        Example:
            ```python
            diff = manifest.diff(
                "data/manifest_old.json",
                "data/manifest_new.json"
            )
            print(f"Added: {len(diff['added'])}")
            print(f"Removed: {len(diff['removed'])}")
            print(f"Modified: {len(diff['modified'])}")
            ```
        """
        # Load manifests
        with open(manifest1_path) as f:
            manifest1 = json.load(f)
        with open(manifest2_path) as f:
            manifest2 = json.load(f)

        # Build file maps
        files1 = {
            (f["symbol"], f.get("timeframe"), f["partition"]): f
            for f in manifest1.get("files", [])
        }
        files2 = {
            (f["symbol"], f.get("timeframe"), f["partition"]): f
            for f in manifest2.get("files", [])
        }

        # Find differences
        keys1 = set(files1.keys())
        keys2 = set(files2.keys())

        added = [files2[k] for k in (keys2 - keys1)]
        removed = [files1[k] for k in (keys1 - keys2)]
        modified = []
        unchanged = 0

        for key in (keys1 & keys2):
            if files1[key].get("version_hash") != files2[key].get("version_hash"):
                modified.append({
                    "file": files2[key],
                    "old_hash": files1[key].get("version_hash"),
                    "new_hash": files2[key].get("version_hash"),
                })
            else:
                unchanged += 1

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged": unchanged,
        }
