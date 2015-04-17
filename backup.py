#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED

def get_date():
    return datetime.today().strftime('%Y_%m_%d_%H_%M_%S')

def compress_file(file_name, output_file):
    with ZipFile(output_file, 'w', ZIP_DEFLATED) as z:
        z.write(file_name)

def compress_folder(folder_name, output_file):
    with ZipFile(output_file, 'w', ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(folder_name):
            for f in files:
                z.write(os.path.join(root, f))

def upload_file(bucket, key, file_name):
    '''
    Upload a file to S3.
    '''
    conn = S3Connection()
    bucket = conn.get_bucket(bucket)
    k = Key(bucket)
    k.key = key
    k.set_contents_from_filename(file_name)

def db_dump(user, pwd, db, output_file):
    '''
    Dump Wordpress database (MySQL/MariaDB).
    '''
    os.popen('mysqldump -u %s -p%s %s > %s' % (user, pwd, db, output_file))

def backup_folder(path, bucket):
    '''
    Backup a folder and upload it to S3.
    '''
    if not os.path.isdir(path):
        raise ValueError('%s must be a directory.' % path)

    dir_name = os.path.basename(os.path.normpath(path))
    temp_file = 'backup_%s_%s.zip' % (dir_name, get_date())
    compress_folder(path, temp_file)
    upload_file(bucket, temp_file, temp_file)
    os.remove(temp_file)

def backup_file(file_name, bucket):
    '''
    Backup a file and upload it to S3.
    '''
    if not os.path.isfile(file_name):
        raise ValueError('%s must be a file.' % file_name)

    temp_file = 'backup_%s_%s.zip' % (file_name, get_date())
    compress_file(file_name, temp_file)
    upload_file(bucket, temp_file, temp_file)
    os.remove(temp_file)

def backup_db(user, pwd, db, bucket):
    '''
    Backup MySQL/MariaDB database and upload it to S3.
    '''
    date = get_date()
    dump_file = 'dump_%s_%s.sql' % (db, date)
    db_dump(user, pwd, db, dump_file)
    temp_file = 'backup_db_%s_%s.zip' % (db, date)
    compress_file(dump_file, temp_file)
    upload_file(bucket, temp_file, temp_file)
    os.remove(dump_file)
    os.remove(temp_file)

def safe_run(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception as e:
        print(e)

def run(args):
    if args.aws_access_key_id:
        os.environ['AWS_ACCESS_KEY_ID'] = args.aws_access_key_id

    if args.aws_secret_access_key:
        os.environ['AWS_SECRET_ACCESS_KEY'] = args.aws_secret_access_key

    if args.file:
        for f in args.file:
            safe_run(backup_file, f, args.bucket)

    if args.dir:
        for d in args.dir:
            safe_run(backup_folder, d, args.bucket)

    if args.db:
        for db in args.db:
            safe_run(backup_db, args.user, args.pwd, db, args.bucket)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backup data to Amazon S3.', epilog='That\'s all folks.')
    parser.add_argument('--bucket', nargs='?', required=True, help='Bucket to upload.')
    parser.add_argument('--file', nargs='+',  help='file(s) to be uploaded')
    parser.add_argument('--dir', nargs='+', help='directory(s) to be uploaded')
    parser.add_argument('--aws_access_key_id', nargs='?',  help='AWS Key (default: AWS_ACCESS_KEY_ID env variable)')
    parser.add_argument('--aws_secret_access_key', nargs='?', help='AWS Secret (default: AWS_SECRET_ACCESS_KEY env variable)')
    db_group = parser.add_argument_group()
    db_group.add_argument('--db', nargs='+', help='database(s) to be uploaded')
    db_group.add_argument('--user', nargs='?', default='root', help='DB user (default: %(default)s)')
    db_group.add_argument('--pwd', nargs='?', help='DB password')
    args = parser.parse_args()

    if not (args.file or args.dir or args.db):
        parser.error("at least one of --file, --dir or --db is required")

    if args.db and not args.pwd:
        parser.error("--db requires --pwd argument")

    run(args)
