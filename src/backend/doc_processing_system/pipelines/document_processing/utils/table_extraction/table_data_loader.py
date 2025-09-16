"""
Table data loader for extracting JSON table data from Docling output files.
Handles different JSON formats and validates table structure.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional


class TableDataLoader:
    """Loads and validates table data from JSON files."""

    def __init__(self):
        """Initialize table data loader."""
        self.logger = logging.getLogger(__name__)

    def load_table_data(self, table_file: Path) -> Optional[List[Dict[str, Any]]]:
        """Load table data from JSON file.

        Args:
            table_file: Path to table JSON file

        Returns:
            List of table dictionaries or None if loading fails
        """
        try:
            with open(table_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Ensure it's a list of tables
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'tables' in data:
                return data['tables']
            else:
                self.logger.warning(f"Unexpected table data format in {table_file}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to load table data from {table_file}: {e}")
            return None

    def find_table_files(self, processing_dir: Path) -> List[Path]:
        """Find all table JSON files in a processing directory.

        Args:
            processing_dir: Directory to search for table files

        Returns:
            List of table file paths
        """
        try:
            table_files = list(processing_dir.glob("*_table_json"))
            self.logger.info(f"Found {len(table_files)} table files in {processing_dir}")
            return table_files
        except Exception as e:
            self.logger.error(f"Failed to find table files in {processing_dir}: {e}")
            return []

    def validate_table_structure(self, tables_data: List[Dict[str, Any]]) -> bool:
        """Validate that table data has expected structure.

        Args:
            tables_data: List of table dictionaries

        Returns:
            True if structure is valid, False otherwise
        """
        if not tables_data:
            return False

        for table in tables_data:
            if not isinstance(table, dict):
                return False

            # Check for required fields
            if 'data' not in table:
                self.logger.warning("Table missing 'data' field")
                return False

            if not isinstance(table['data'], list):
                self.logger.warning("Table 'data' is not a list")
                return False

        return True


    def extract_billing_data(self, records):
        """
        Extracts specific billing fields from a list of records.

        Args:
            records: A list of dictionaries representing the JSON data.

        Returns:
            A dictionary containing the extracted fields.
        """
        output = {
            'penggunaan_puncak_tanpa_st': 0.00,
            'penggunaan_puncak_dengan_st': 0.00,
            'jumlah_penggunaan_puncak': 0.00,
            'penggunaan_luar_puncak_tanpa_st': 0.00,
            'penggunaan_luar_puncak_dengan_st': 0.00,
            'jumlah_penggunaan_luar_puncak': 0.00,
            'penggunaan_tanpa_st': 0.00,
            'penggunaan_dengan_st': 0.00,
            'jumlah_penggunaan': 0.00,
            'permintaan_maksima_tanpa_st': 0.00,
            'permintaan_maksima_dengan_st': 0.00,
            'jumlah_permintaan_maksima': 0.00,
            'caj_tenaga_puncak_tanpa_st': 0.00,
            'caj_tenaga_puncak_dengan_st': 0.00,
            'jumlah_caj_tenaga_puncak': 0.00,
            'caj_tenaga_luar_puncak_tanpa_st': 0.00,
            'caj_tenaga_luar_puncak_dengan_st': 0.00,
            'jumlah_caj_tenaga_luar_puncak': 0.00,
            'caj_afa_tanpa_st': 0.00,
            'caj_afa_dengan_st': 0.00,
            'jumlah_caj_afa': 0.00,
            'caj_kapasiti_tanpa_st': 0.00,
            'caj_kapasiti_dengan_st': 0.00,
            'jumlah_caj_kapasiti': 0.00,
            'caj_rangkaian_tanpa_st': 0.00,
            'caj_rangkaian_dengan_st': 0.00,
            'jumlah_caj_rangkaian': 0.00,
            'caj_peruncitan_tanpa_st': 0.00,
            'caj_peruncitan_dengan_st': 0.00,
            'jumlah_caj_peruncitan': 0.00,
            'caj_penggunaan_bulan_semasa': 0.00,
            'kwtbb': 0.00,
            'beban_diisytiharkan_kw': 0.00,
            'kehendak_maksima_tertinggi_kw': 0.00,
            'faktor_beban': 0.00,
            'angkadar_kuasa': 0.00,
            'average_smp': 0.00,
            'maq_kwh': 0.00
        }

        try:
            for table in records:
                if 'data' not in table:
                    continue

                table_data = table['data']
                table_id = table.get('table_id', -1)

                # Table 2: Extract technical parameters by index
                if table_id == 2:
                    if len(table_data) >= 5:
                        # Extract MAQ from column header (key name "57,413.00")
                        row_0_keys = list(table_data[0].keys())
                        if len(row_0_keys) >= 2:
                            maq_header = row_0_keys[1]  # "57,413.00"
                            output['maq_kwh'] = self._safe_float(maq_header.replace(',', ''))

                        # Extract values from the second column (index 1)
                        row_0_values = list(table_data[0].values())
                        # Row 0: Average SMP
                        if len(row_0_values) >= 2:
                            output['average_smp'] = self._safe_float(row_0_values[1])

                        # Row 1: Beban Diisytiharkan
                        if len(table_data) > 1:
                            row_1_values = list(table_data[1].values())
                            if len(row_1_values) >= 2:
                                output['beban_diisytiharkan_kw'] = self._extract_numeric(row_1_values[1])

                        # Row 2: Kehendak Maksima Tertinggi
                        if len(table_data) > 2:
                            row_2_values = list(table_data[2].values())
                            if len(row_2_values) >= 2:
                                output['kehendak_maksima_tertinggi_kw'] = self._extract_numeric(row_2_values[1])

                        # Row 3: Faktor Beban
                        if len(table_data) > 3:
                            row_3_values = list(table_data[3].values())
                            if len(row_3_values) >= 2:
                                output['faktor_beban'] = self._safe_float(row_3_values[1])

                        # Row 4: Angkadar Kuasa
                        if len(table_data) > 4:
                            row_4_values = list(table_data[4].values())
                            if len(row_4_values) >= 2:
                                output['angkadar_kuasa'] = self._safe_float(row_4_values[1])

                # Table 3: Extract usage and charges by index
                elif table_id == 3:
                    if len(table_data) >= 4:
                        # Row 0: Puncak (kWh)
                        if len(table_data) > 0:
                            row_values = list(table_data[0].values())
                            if len(row_values) >= 4:
                                output['jumlah_penggunaan_puncak'] = self._safe_float(row_values[1])
                                output['jumlah_caj_tenaga_puncak'] = self._safe_float(row_values[3])

                        # Row 1: Luar Puncak (kWh)
                        if len(table_data) > 1:
                            row_values = list(table_data[1].values())
                            if len(row_values) >= 4:
                                output['jumlah_penggunaan_luar_puncak'] = self._safe_float(row_values[1])
                                output['jumlah_caj_tenaga_luar_puncak'] = self._safe_float(row_values[3])

                        # Row 2: Kehendak Maksima (kW)
                        if len(table_data) > 2:
                            row_values = list(table_data[2].values())
                            if len(row_values) >= 2:
                                output['jumlah_permintaan_maksima'] = self._safe_float(row_values[1])

                # Table 5: Extract charges breakdown by index
                elif table_id == 5:
                    charge_types = [
                        ('caj_afa_tanpa_st', 'caj_afa_dengan_st', 'jumlah_caj_afa'),
                        ('caj_kapasiti_tanpa_st', 'caj_kapasiti_dengan_st', 'jumlah_caj_kapasiti'),
                        ('caj_rangkaian_tanpa_st', 'caj_rangkaian_dengan_st', 'jumlah_caj_rangkaian'),
                        ('caj_peruncitan_tanpa_st', 'caj_peruncitan_dengan_st', 'jumlah_caj_peruncitan')
                    ]

                    for i, (tanpa_key, dengan_key, jumlah_key) in enumerate(charge_types):
                        if i < len(table_data):
                            row_values = list(table_data[i].values())
                            if len(row_values) >= 4:
                                tanpa_st = self._safe_float(row_values[1])
                                dengan_st = self._safe_float(row_values[2])
                                output[tanpa_key] = tanpa_st
                                output[dengan_key] = dengan_st
                                output[jumlah_key] = tanpa_st + dengan_st

                # Table 6: Extract meter readings by index
                elif table_id == 6:
                    for i, row in enumerate(table_data):
                        row_values = list(row.values())
                        if len(row_values) >= 5:
                            unit = row_values[4]
                            consumption = row_values[3]

                            if 'kWh P (I)' in unit:  # Peak usage (row 1)
                                output['penggunaan_puncak_tanpa_st'] = self._safe_float(consumption)

                            elif 'kWh 0 (I)' in unit:  # Off-peak usage (row 2)
                                output['penggunaan_luar_puncak_tanpa_st'] = self._safe_float(consumption)

            # Calculate totals
            output['jumlah_penggunaan'] = output['jumlah_penggunaan_puncak'] + output['jumlah_penggunaan_luar_puncak']
            output['penggunaan_tanpa_st'] = output['penggunaan_puncak_tanpa_st'] + output['penggunaan_luar_puncak_tanpa_st']

            # Structured printing
            self._print_structured_results(output)
        except Exception as e:
            self.logger.error(f"Error extracting billing data: {e}")

        return output

    # HELPER FUNCTIONS
    def _safe_float(self, value):
        """Convert string value to float, handling common formatting issues."""
        if not value or value == '':
            return 0.00

        try:
            # Remove commas and convert to float
            cleaned_value = str(value).replace(',', '').replace('RM', '').strip()
            return float(cleaned_value)
        except (ValueError, TypeError):
            return 0.00

    def _extract_numeric(self, value):
        """Extract numeric value from strings like '950.00kW'."""
        if not value:
            return 0.00

        try:
            # Remove units and convert to float
            cleaned_value = str(value).replace('kW', '').replace('kWh', '').replace(',', '').strip()
            return float(cleaned_value)
        except (ValueError, TypeError):
            return 0.00

    def _print_structured_results(self, output):
        """Print results in structured format."""
        print("\n" + "="*80)
        print("BILLING DATA EXTRACTION RESULTS")
        print("="*80)

        # Usage Section
        print("\n📊 USAGE DATA:")
        print(f"  Peak Usage (Tanpa ST):          {output['penggunaan_puncak_tanpa_st']:>12.2f} kWh")
        print(f"  Peak Usage (Dengan ST):         {output['penggunaan_puncak_dengan_st']:>12.2f} kWh")
        print(f"  Total Peak Usage:               {output['jumlah_penggunaan_puncak']:>12.2f} kWh")
        print(f"  Off-Peak Usage (Tanpa ST):      {output['penggunaan_luar_puncak_tanpa_st']:>12.2f} kWh")
        print(f"  Off-Peak Usage (Dengan ST):     {output['penggunaan_luar_puncak_dengan_st']:>12.2f} kWh")
        print(f"  Total Off-Peak Usage:           {output['jumlah_penggunaan_luar_puncak']:>12.2f} kWh")
        print(f"  TOTAL USAGE:                    {output['jumlah_penggunaan']:>12.2f} kWh")

        # Demand Section
        print(f"\n⚡ DEMAND DATA:")
        print(f"  Max Demand (Tanpa ST):          {output['permintaan_maksima_tanpa_st']:>12.2f} kW")
        print(f"  Max Demand (Dengan ST):         {output['permintaan_maksima_dengan_st']:>12.2f} kW")
        print(f"  Total Max Demand:               {output['jumlah_permintaan_maksima']:>12.2f} kW")

        # Technical Parameters
        print(f"\n🔧 TECHNICAL PARAMETERS:")
        print(f"  Declared Load:                  {output['beban_diisytiharkan_kw']:>12.2f} kW")
        print(f"  Highest Max Demand:             {output['kehendak_maksima_tertinggi_kw']:>12.2f} kW")
        print(f"  Load Factor:                    {output['faktor_beban']:>12.4f}")
        print(f"  Power Factor:                   {output['angkadar_kuasa']:>12.4f}")
        print(f"  Average SMP:                    {output['average_smp']:>12.4f}")
        print(f"  MAQ:                            {output['maq_kwh']:>12.2f} kWh")

        # Charges Section
        print(f"\n💰 CHARGES BREAKDOWN:")
        print(f"  Energy Charges (Tanpa ST):      RM {output['caj_afa_tanpa_st']:>10.2f}")
        print(f"  Energy Charges (Dengan ST):     RM {output['caj_afa_dengan_st']:>10.2f}")
        print(f"  Total Energy Charges:           RM {output['jumlah_caj_afa']:>10.2f}")

        print(f"  Capacity Charges (Tanpa ST):    RM {output['caj_kapasiti_tanpa_st']:>10.2f}")
        print(f"  Capacity Charges (Dengan ST):   RM {output['caj_kapasiti_dengan_st']:>10.2f}")
        print(f"  Total Capacity Charges:         RM {output['jumlah_caj_kapasiti']:>10.2f}")

        print(f"  Network Charges (Tanpa ST):     RM {output['caj_rangkaian_tanpa_st']:>10.2f}")
        print(f"  Network Charges (Dengan ST):    RM {output['caj_rangkaian_dengan_st']:>10.2f}")
        print(f"  Total Network Charges:          RM {output['jumlah_caj_rangkaian']:>10.2f}")

        print(f"  Retail Charges (Tanpa ST):      RM {output['caj_peruncitan_tanpa_st']:>10.2f}")
        print(f"  Retail Charges (Dengan ST):     RM {output['caj_peruncitan_dengan_st']:>10.2f}")
        print(f"  Total Retail Charges:           RM {output['jumlah_caj_peruncitan']:>10.2f}")

        print("="*80)

    # The input JSON data provided by the user

if __name__ == "__main__":
    try:
        loader = TableDataLoader()
        result=loader.load_table_data(Path(r"C:\Users\User\Projects\scaled_processing\data\temp\docling\GSPP_0602_202507_Billing_eabe7387\GSPP_0602_202507_Billing_eabe7387_table_json"))
        print(loader.extract_billing_data(records=result))
    except Exception as e:
        print(e)