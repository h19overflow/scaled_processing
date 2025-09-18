"""
Table data loader for extracting JSON table data from Docling output files.
Handles different JSON formats and validates table structure.
"""

import json
import logging
import csv
from datetime import datetime
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
        found_params = []

        for row in table_data:
            # Look for MAQ as column header (edge case)
            for key, value in row.items():
                # Check if key looks like MAQ (numeric with comma)
                if ',' in key and key.replace(',', '').replace('.', '').isdigit():
                    output['maq_kwh'] = self._safe_float(key.replace(',', ''))
                    found_params.append(f"MAQ: {output['maq_kwh']:.2f} kWh (from column header)")

                # Check for technical parameter patterns in values
                if 'Average System Marginal Price' in str(value) or 'SMP' in str(value):
                    # Find the corresponding value (usually in the same row)
                    row_values = list(row.values())
                    for val in row_values:
                        if val != value and val and self._is_numeric(val):
                            output['average_smp'] = self._safe_float(val)
                            found_params.append(f"Average SMP: {output['average_smp']:.4f}")
                            break

                elif 'Beban Diisytiharkan' in str(value):
                    # Look in the same row for kW value
                    for val in row.values():
                        if 'kW' in str(val) and val != value:
                            extracted_val = self._extract_numeric(val)
                            output['beban_diisytiharkan_kw'] = extracted_val
                            found_params.append(f"Declared Load: {extracted_val:.2f} kW (from '{val}')")
                            break

                elif 'Kehendak Maksima Tertinggi' in str(value):
                    # Look in the same row for kW value
                    for val in row.values():
                        if 'kW' in str(val) and val != value:
                            extracted_val = self._extract_numeric(val)
                            output['kehendak_maksima_tertinggi_kw'] = extracted_val
                            found_params.append(f"Highest Max Demand: {extracted_val:.2f} kW (from '{val}')")
                            break

                elif 'Faktor Beban' in str(value):
                    row_values = list(row.values())
                    for val in row_values:
                        if val != value and val and self._is_numeric(val):
                            output['faktor_beban'] = self._safe_float(val)
                            found_params.append(f"Load Factor: {output['faktor_beban']:.4f}")
                            break

                elif 'Angkadar Kuasa' in str(value):
                    row_values = list(row.values())
                    for val in row_values:
                        if val != value and val and self._is_numeric(val):
                            output['angkadar_kuasa'] = self._safe_float(val)
                            found_params.append(f"Power Factor: {output['angkadar_kuasa']:.4f}")
                            break

        if found_params:
            self.logger.info(f"Technical parameters found: {', '.join(found_params)}")
        else:
            self.logger.warning("No technical parameters found in any table")

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
                        amount = self._safe_float(row['Amaun (RM)'])
                        output['jumlah_caj_tenaga_puncak'] = amount
                        # Map to energy charge fields (peak charges go to "tanpa ST")
                        output['caj_tenaga_puncak_tanpa_st'] = amount
                        output['jumlah_caj_tenaga_puncak'] = amount

                elif 'Luar Puncak (kWh)' in str(value):
                    # Off-peak usage
                    if 'Penggunaan' in row:
                        output['jumlah_penggunaan_luar_puncak'] = self._safe_float(row['Penggunaan'])
                    if 'Amaun (RM)' in row:
                        amount = self._safe_float(row['Amaun (RM)'])
                        output['jumlah_caj_tenaga_luar_puncak'] = amount
                        # Map to energy charge fields (off-peak charges go to "tanpa ST")
                        output['caj_tenaga_luar_puncak_tanpa_st'] = amount
                        output['jumlah_caj_tenaga_luar_puncak'] = amount

                elif 'Pertengahan Puncak (kWh)' in str(value):
                    # Mid-peak usage (add to peak for now)
                    if 'Penggunaan' in row:
                        current_peak = output.get('jumlah_penggunaan_puncak', 0.0)
                        output['jumlah_penggunaan_puncak'] = current_peak + self._safe_float(row['Penggunaan'])
                    if 'Amaun (RM)' in row:
                        amount = self._safe_float(row['Amaun (RM)'])
                        current_peak_charge = output.get('jumlah_caj_tenaga_puncak', 0.0)
                        current_peak_charge_tanpa_st = output.get('caj_tenaga_puncak_tanpa_st', 0.0)
                        output['jumlah_caj_tenaga_puncak'] = current_peak_charge + amount
                        output['caj_tenaga_puncak_tanpa_st'] = current_peak_charge_tanpa_st + amount

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
        """Extract numeric value from strings like '950.00kW' or '950.OOkW'."""
        if not value:
            return 0.00

        try:
            # Remove units and clean common character substitutions
            cleaned_value = str(value).replace('kW', '').replace('kWh', '').replace(',', '').strip()

            # Handle common OCR errors: O instead of 0
            cleaned_value = cleaned_value.replace('O', '0')

            return float(cleaned_value)
        except (ValueError, TypeError):
            # If direct conversion fails, try to extract just the numeric part
            import re
            numbers = re.findall(r'\d+\.?\d*', str(value).replace('O', '0'))
            if numbers:
                return float(numbers[0])
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

    def export_to_csv(self, output_data: Dict[str, Any], source_file_path: Path) -> Path:
        """Export extracted billing data to CSV file in same directory as source JSON."""
        try:
            # Create CSV filename based on source file
            csv_filename = source_file_path.name.replace('_table_json', '_billing_data.csv')
            csv_path = source_file_path.parent / csv_filename

            # Prepare structured data for CSV export
            csv_data = []

            # Add metadata row
            csv_data.append({
                'Category': 'METADATA',
                'Field': 'source_file',
                'Value': source_file_path.name,
                'Unit': '',
                'Notes': f'Extracted on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            })

            # Usage Data Section
            usage_fields = [
                ('penggunaan_puncak_tanpa_st', 'Peak Usage (Tanpa ST)', 'kWh'),
                ('penggunaan_puncak_dengan_st', 'Peak Usage (Dengan ST)', 'kWh'),
                ('jumlah_penggunaan_puncak', 'Total Peak Usage', 'kWh'),
                ('penggunaan_luar_puncak_tanpa_st', 'Off-Peak Usage (Tanpa ST)', 'kWh'),
                ('penggunaan_luar_puncak_dengan_st', 'Off-Peak Usage (Dengan ST)', 'kWh'),
                ('jumlah_penggunaan_luar_puncak', 'Total Off-Peak Usage', 'kWh'),
                ('jumlah_penggunaan', 'TOTAL USAGE', 'kWh')
            ]

            for field_key, field_name, unit in usage_fields:
                csv_data.append({
                    'Category': 'USAGE_DATA',
                    'Field': field_name,
                    'Value': f"{output_data[field_key]:.2f}",
                    'Unit': unit,
                    'Notes': ''
                })

            # Demand Data Section
            demand_fields = [
                ('permintaan_maksima_tanpa_st', 'Max Demand (Tanpa ST)', 'kW'),
                ('permintaan_maksima_dengan_st', 'Max Demand (Dengan ST)', 'kW'),
                ('jumlah_permintaan_maksima', 'Total Max Demand', 'kW')
            ]

            for field_key, field_name, unit in demand_fields:
                csv_data.append({
                    'Category': 'DEMAND_DATA',
                    'Field': field_name,
                    'Value': f"{output_data[field_key]:.2f}",
                    'Unit': unit,
                    'Notes': ''
                })

            # Technical Parameters Section
            technical_fields = [
                ('beban_diisytiharkan_kw', 'Declared Load', 'kW'),
                ('kehendak_maksima_tertinggi_kw', 'Highest Max Demand', 'kW'),
                ('faktor_beban', 'Load Factor', ''),
                ('angkadar_kuasa', 'Power Factor', ''),
                ('average_smp', 'Average SMP', 'RM/kWh'),
                ('maq_kwh', 'Maximum Allowable Quantity (MAQ)', 'kWh')
            ]

            for field_key, field_name, unit in technical_fields:
                csv_data.append({
                    'Category': 'TECHNICAL_PARAMETERS',
                    'Field': field_name,
                    'Value': f"{output_data[field_key]:.4f}" if field_key in ['faktor_beban', 'angkadar_kuasa', 'average_smp'] else f"{output_data[field_key]:.2f}",
                    'Unit': unit,
                    'Notes': 'Missing from source' if output_data[field_key] == 0.0 and field_key in ['beban_diisytiharkan_kw', 'kehendak_maksima_tertinggi_kw', 'average_smp', 'maq_kwh'] else ''
                })

            # Charges Breakdown Section
            charge_fields = [
                ('caj_tenaga_puncak_tanpa_st', 'Energy Peak Charges (Tanpa ST)', 'RM'),
                ('caj_tenaga_puncak_dengan_st', 'Energy Peak Charges (Dengan ST)', 'RM'),
                ('jumlah_caj_tenaga_puncak', 'Total Energy Peak Charges', 'RM'),
                ('caj_tenaga_luar_puncak_tanpa_st', 'Energy Off-Peak Charges (Tanpa ST)', 'RM'),
                ('caj_tenaga_luar_puncak_dengan_st', 'Energy Off-Peak Charges (Dengan ST)', 'RM'),
                ('jumlah_caj_tenaga_luar_puncak', 'Total Energy Off-Peak Charges', 'RM'),
                ('caj_afa_tanpa_st', 'AFA Charges (Tanpa ST)', 'RM'),
                ('caj_afa_dengan_st', 'AFA Charges (Dengan ST)', 'RM'),
                ('jumlah_caj_afa', 'Total AFA Charges', 'RM'),
                ('caj_kapasiti_tanpa_st', 'Capacity Charges (Tanpa ST)', 'RM'),
                ('caj_kapasiti_dengan_st', 'Capacity Charges (Dengan ST)', 'RM'),
                ('jumlah_caj_kapasiti', 'Total Capacity Charges', 'RM'),
                ('caj_rangkaian_tanpa_st', 'Network Charges (Tanpa ST)', 'RM'),
                ('caj_rangkaian_dengan_st', 'Network Charges (Dengan ST)', 'RM'),
                ('jumlah_caj_rangkaian', 'Total Network Charges', 'RM'),
                ('caj_peruncitan_tanpa_st', 'Retail Charges (Tanpa ST)', 'RM'),
                ('caj_peruncitan_dengan_st', 'Retail Charges (Dengan ST)', 'RM'),
                ('jumlah_caj_peruncitan', 'Total Retail Charges', 'RM')
            ]

            for field_key, field_name, unit in charge_fields:
                csv_data.append({
                    'Category': 'CHARGES_BREAKDOWN',
                    'Field': field_name,
                    'Value': f"{output_data[field_key]:.2f}",
                    'Unit': unit,
                    'Notes': ''
                })

            # Write CSV file
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Category', 'Field', 'Value', 'Unit', 'Notes']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for row in csv_data:
                    writer.writerow(row)

            self.logger.info(f"Exported billing data to CSV: {csv_path}")
            print(f"\n✅ CSV exported successfully: {csv_path}")
            return csv_path

        except Exception as e:
            self.logger.error(f"Failed to export CSV: {e}")
            print(f"❌ CSV export failed: {e}")
            return None

    # The input JSON data provided by the user

if __name__ == "__main__":
    try:
        loader = TableDataLoader()

        # Test with first invoice format
        print("=" * 50)
        print("TESTING FIRST INVOICE FORMAT")
        print("=" * 50)
        file1_path = Path(r"C:\Users\User\Projects\scaled_processing\data\temp\docling\GSPP_0602_202507_Billing_eabe7387\GSPP_0602_202507_Billing_eabe7387_table_json")
        result1 = loader.load_table_data(file1_path)
        output1 = loader.extract_billing_data(records=result1)

        # Export to CSV
        csv_path1 = loader.export_to_csv(output1, file1_path)

        print("\n" + "=" * 50)
        print("TESTING SECOND INVOICE FORMAT")
        print("=" * 50)
        # Test with second invoice format
        file2_path = Path(r"C:\Users\User\Projects\scaled_processing\data\temp\docling\GSPP_0901_202507_Billing_cfd35657\GSPP_0901_202507_Billing_cfd35657_table_json")
        result2 = loader.load_table_data(file2_path)
        output2 = loader.extract_billing_data(records=result2)

        # Export to CSV
        csv_path2 = loader.export_to_csv(output2, file2_path)

        print("\n" + "=" * 50)
        print("COMPARISON SUMMARY")
        print("=" * 50)
        print(f"First invoice - Total Usage: {output1['jumlah_penggunaan']:,.0f} kWh")
        print(f"Second invoice - Total Usage: {output2['jumlah_penggunaan']:,.0f} kWh")
        print(f"First invoice - MAQ: {output1['maq_kwh']:,.0f} kWh")
        print(f"Second invoice - MAQ: {output2['maq_kwh']:,.0f} kWh")

    except Exception as e:
        print(e)