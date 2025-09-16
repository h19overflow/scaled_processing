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


#TODO Beban Diisytiharkan 950.00kW
# Kehendak Maksima Tertinggi 819.00kW
# NOT CAPTURED in 0602_202507
# AMAUN COLUMN AND KADAR NOT CAPTURED IN THE ANDA GUNA TABLE
# INFO IS IN THE JSON BUT not LOADED     {
#         "Penerangan": "Puncak (kWh)",
#         "Penggunaan": "141,779.00",
#         "Kadar (RM)": "0.35500",
#         "Amaun (RM)": "50,331.55"},
#  {,
#         "Penerangan": "Jumlah",
#         "Penggunaan": "277,411.00",
#         "Kadar (RM)": "",
#         "Amaun (RM)": "106,526.96"
#       }
#     ]

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
            # Scan all tables for flexible content-pattern extraction
            for table in records:
                if 'data' not in table:
                    continue

                table_data = table['data']
                self._extract_from_table(table_data, output)

            # Calculate totals after all extraction
            self._calculate_totals(output)

            # Structured printing
            self._print_structured_results(output)
        except Exception as e:
            self.logger.error(f"Error extracting billing data: {e}")

        return output

    def _extract_from_table(self, table_data, output):
        """Extract data from a single table using pattern recognition."""
        if not table_data:
            return

        # Check if this is a technical parameters table (has MAQ structure)
        self._extract_technical_parameters(table_data, output)

        # Check if this is a usage data table
        self._extract_usage_data(table_data, output)

        # Check if this is a charge breakdown table
        self._extract_charge_breakdown(table_data, output)

        # Check if this is a meter readings table
        self._extract_meter_readings(table_data, output)

    def _extract_technical_parameters(self, table_data, output):
        """Extract technical parameters like MAQ, Load Factor, etc."""
        for row in table_data:
            # Look for MAQ as column header (edge case)
            for key, value in row.items():
                # Check if key looks like MAQ (numeric with comma)
                if ',' in key and key.replace(',', '').replace('.', '').isdigit():
                    output['maq_kwh'] = self._safe_float(key.replace(',', ''))

                # Check for technical parameter patterns in values
                if 'Average System Marginal Price' in str(value) or 'SMP' in str(value):
                    # Find the corresponding value (usually in the same row)
                    row_values = list(row.values())
                    for val in row_values:
                        if val != value and val and self._is_numeric(val):
                            output['average_smp'] = self._safe_float(val)
                            break

                elif 'Beban Diisytiharkan' in str(value):
                    # Look in the same row for kW value
                    for val in row.values():
                        if 'kW' in str(val) and val != value:
                            output['beban_diisytiharkan_kw'] = self._extract_numeric(val)
                            break

                elif 'Kehendak Maksima Tertinggi' in str(value):
                    # Look in the same row for kW value
                    for val in row.values():
                        if 'kW' in str(val) and val != value:
                            output['kehendak_maksima_tertinggi_kw'] = self._extract_numeric(val)
                            break

                elif 'Faktor Beban' in str(value):
                    row_values = list(row.values())
                    for val in row_values:
                        if val != value and val and self._is_numeric(val):
                            output['faktor_beban'] = self._safe_float(val)
                            break

                elif 'Angkadar Kuasa' in str(value):
                    row_values = list(row.values())
                    for val in row_values:
                        if val != value and val and self._is_numeric(val):
                            output['angkadar_kuasa'] = self._safe_float(val)
                            break

    def _extract_usage_data(self, table_data, output):
        """Extract usage data (Peak, Mid-Peak, Off-Peak)."""
        for row in table_data:
            for key, value in row.items():
                # Look for usage patterns
                if 'Puncak (kWh)' in str(value) and 'Luar' not in str(value) and 'Pertengahan' not in str(value):
                    # Peak usage
                    if 'Penggunaan' in row:
                        output['jumlah_penggunaan_puncak'] = self._safe_float(row['Penggunaan'])
                    if 'Amaun (RM)' in row:
                        output['jumlah_caj_tenaga_puncak'] = self._safe_float(row['Amaun (RM)'])

                elif 'Luar Puncak (kWh)' in str(value):
                    # Off-peak usage
                    if 'Penggunaan' in row:
                        output['jumlah_penggunaan_luar_puncak'] = self._safe_float(row['Penggunaan'])
                    if 'Amaun (RM)' in row:
                        output['jumlah_caj_tenaga_luar_puncak'] = self._safe_float(row['Amaun (RM)'])

                elif 'Pertengahan Puncak (kWh)' in str(value):
                    # Mid-peak usage (add to peak for now)
                    if 'Penggunaan' in row:
                        current_peak = output.get('jumlah_penggunaan_puncak', 0.0)
                        output['jumlah_penggunaan_puncak'] = current_peak + self._safe_float(row['Penggunaan'])
                    if 'Amaun (RM)' in row:
                        current_peak_charge = output.get('jumlah_caj_tenaga_puncak', 0.0)
                        output['jumlah_caj_tenaga_puncak'] = current_peak_charge + self._safe_float(row['Amaun (RM)'])

                elif 'Kehendak Maksima (kW)' in str(value):
                    # Maximum demand
                    if 'Penggunaan' in row:
                        output['jumlah_permintaan_maksima'] = self._safe_float(row['Penggunaan'])

    def _extract_charge_breakdown(self, table_data, output):
        """Extract charge breakdown (Tanpa ST/Dengan ST)."""
        # Check if this table has charge breakdown structure
        has_tanpa_st = any('Tanpa ST' in str(row) for row in table_data)
        has_dengan_st = any('Dengan ST' in str(row) for row in table_data)

        if not (has_tanpa_st and has_dengan_st):
            return

        # Map charges by row order
        charge_mappings = [
            ('caj_afa_tanpa_st', 'caj_afa_dengan_st', 'jumlah_caj_afa'),
            ('caj_kapasiti_tanpa_st', 'caj_kapasiti_dengan_st', 'jumlah_caj_kapasiti'),
            ('caj_rangkaian_tanpa_st', 'caj_rangkaian_dengan_st', 'jumlah_caj_rangkaian'),
            ('caj_peruncitan_tanpa_st', 'caj_peruncitan_dengan_st', 'jumlah_caj_peruncitan')
        ]

        valid_rows = [row for row in table_data if 'Tanpa ST' in row and 'Dengan ST' in row and row.get('Tanpa ST') and row.get('Dengan ST')]

        for i, (tanpa_key, dengan_key, jumlah_key) in enumerate(charge_mappings):
            if i < len(valid_rows):
                row = valid_rows[i]
                tanpa_st = self._safe_float(row.get('Tanpa ST', ''))
                dengan_st = self._safe_float(row.get('Dengan ST', ''))

                if tanpa_st > 0 or dengan_st > 0:  # Only assign if we have valid data
                    output[tanpa_key] = tanpa_st
                    output[dengan_key] = dengan_st
                    output[jumlah_key] = tanpa_st + dengan_st

    def _extract_meter_readings(self, table_data, output):
        """Extract meter readings by unit pattern matching."""
        for row in table_data:
            unit = row.get('Unit', '')

            # Look for consumption column (could be unnamed or named differently)
            consumption_value = None
            for key, value in row.items():
                if key in ['Penggunaan', ''] and value and value != unit:
                    consumption_value = value
                    break

            if consumption_value:
                if 'kWh P (I)' in unit:  # Peak usage
                    output['penggunaan_puncak_tanpa_st'] = self._safe_float(consumption_value)
                elif 'kWh 0 (I)' in unit:  # Off-peak usage
                    output['penggunaan_luar_puncak_tanpa_st'] = self._safe_float(consumption_value)

    def _calculate_totals(self, output):
        """Calculate derived totals."""
        # Usage totals
        output['jumlah_penggunaan'] = output['jumlah_penggunaan_puncak'] + output['jumlah_penggunaan_luar_puncak']
        output['penggunaan_tanpa_st'] = output['penggunaan_puncak_tanpa_st'] + output['penggunaan_luar_puncak_tanpa_st']

        # If meter readings exist but usage data is missing, copy from meter readings
        if output['penggunaan_puncak_tanpa_st'] > 0 and output['jumlah_penggunaan_puncak'] == 0:
            output['jumlah_penggunaan_puncak'] = output['penggunaan_puncak_tanpa_st']

        if output['penggunaan_luar_puncak_tanpa_st'] > 0 and output['jumlah_penggunaan_luar_puncak'] == 0:
            output['jumlah_penggunaan_luar_puncak'] = output['penggunaan_luar_puncak_tanpa_st']

    def _is_numeric(self, value):
        """Check if a value can be converted to a number."""
        if not value:
            return False
        try:
            cleaned = str(value).replace(',', '').replace('RM', '').replace('~', '').strip()
            float(cleaned)
            return True
        except (ValueError, TypeError):
            return False

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

        # Test with first invoice format
        print("=" * 50)
        print("TESTING FIRST INVOICE FORMAT")
        print("=" * 50)
        result1 = loader.load_table_data(Path(r"C:\Users\User\Projects\scaled_processing\data\temp\docling\GSPP_0602_202507_Billing_eabe7387\GSPP_0602_202507_Billing_eabe7387_table_json"))
        output1 = loader.extract_billing_data(records=result1)

        print("\n" + "=" * 50)
        print("TESTING SECOND INVOICE FORMAT")
        print("=" * 50)
        # Test with second invoice format
        result2 = loader.load_table_data(Path(r"C:\Users\User\Projects\scaled_processing\data\temp\docling\GSPP_0901_202507_Billing_cfd35657\GSPP_0901_202507_Billing_cfd35657_table_json"))
        output2 = loader.extract_billing_data(records=result2)

        print("\n" + "=" * 50)
        print("COMPARISON SUMMARY")
        print("=" * 50)
        print(f"First invoice - Total Usage: {output1['jumlah_penggunaan']:,.0f} kWh")
        print(f"Second invoice - Total Usage: {output2['jumlah_penggunaan']:,.0f} kWh")
        print(f"First invoice - MAQ: {output1['maq_kwh']:,.0f} kWh")
        print(f"Second invoice - MAQ: {output2['maq_kwh']:,.0f} kWh")

    except Exception as e:
        print(e)