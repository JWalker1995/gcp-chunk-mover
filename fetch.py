import sys
import subprocess
import re
import time

if len(sys.argv) != 3:
  print('Usage: python3 fetch.py [gcp_instance_name] [base_path]', file=sys.stderr)
  exit(1)

gcp_instance_name = sys.argv[1]
base_path = sys.argv[2]

script = f'sort <(ls {base_path}/*) <(sudo lsof -F cn -- {base_path}/* | grep "^n" | cut -c 2-) | uniq --unique'
script = f"bash -c '{script}'"

chunk_pattern = re.compile('\\/chunk_.+_(\\d+)\\.bin$')
threshold = time.time() - 60 * 60 * 24

scp_files = []

out = subprocess.run(['gcloud', 'compute', 'ssh', gcp_instance_name, '--', script], capture_output=True)
for file in out.stdout.split(b'\n'):
  file = file.decode('utf-8').strip()
  if not file:
    continue
  m = chunk_pattern.search(file)
  if not m:
    raise Exception(f'Cannot match {file} as a chunk filepath')
  time = int(m[1]) / 1e6
  if time > threshold:
    continue
  scp_files.append(file)

if scp_files:
  subprocess.run(['gcloud', 'compute', 'scp', *[f'{gcp_instance_name}:{file}' for file in scp_files], f'{base_path}/'], check=True)
  subprocess.run(['gcloud', 'compute', 'ssh', gcp_instance_name, '--', f'sudo rm {" ".join(scp_files)}'], check=True)
