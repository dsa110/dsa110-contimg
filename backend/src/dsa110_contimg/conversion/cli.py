import argparse
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import convert_subband_groups_to_ms
from dsa110_contimg.conversion.strategies.streaming_converter import start_streaming_conversion

def main():
    parser = argparse.ArgumentParser(description="Command-line interface for DSA-110 conversion process.")
    
    subparsers = parser.add_subparsers(dest='command')

    # Subparser for batch conversion
    batch_parser = subparsers.add_parser('batch', help='Convert subband groups to Measurement Sets')
    batch_parser.add_argument('input_dir', type=str, help='Directory containing input HDF5 files')
    batch_parser.add_argument('output_dir', type=str, help='Directory to save output Measurement Sets')
    batch_parser.add_argument('start_time', type=str, help='Start time for conversion (ISO format)')
    batch_parser.add_argument('end_time', type=str, help='End time for conversion (ISO format)')

    # Subparser for streaming conversion
    stream_parser = subparsers.add_parser('stream', help='Start streaming conversion process')
    stream_parser.add_argument('--input-dir', type=str, required=True, help='Directory for incoming HDF5 files')
    stream_parser.add_argument('--output-dir', type=str, required=True, help='Directory for output Measurement Sets')
    stream_parser.add_argument('--queue-db', type=str, required=True, help='SQLite database for queue management')
    stream_parser.add_argument('--registry-db', type=str, required=True, help='SQLite database for calibration registry')
    stream_parser.add_argument('--scratch-dir', type=str, help='Temporary directory for processing')

    args = parser.parse_args()

    if args.command == 'batch':
        convert_subband_groups_to_ms(args.input_dir, args.output_dir, args.start_time, args.end_time)
    elif args.command == 'stream':
        start_streaming_conversion(args.input_dir, args.output_dir, args.queue_db, args.registry_db, args.scratch_dir)

if __name__ == "__main__":
    main()