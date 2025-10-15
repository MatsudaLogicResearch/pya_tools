#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#===================================================================
# This file is associated with the pya_toos project.
# Copyright (C) 2025 Logic-Research K.K. (Author: MATSUDA Masahiro)
# 
# This script file is licensed under the MIT License.
#===================================================================
#[Description]
# runs klayout with 
#===================================================================

import argparse
import subprocess
import sys
import importlib.resources as resources
import shutil
from pathlib import Path
import os

# ------------------------
# functions
# ------------------------
def list_available_scripts():
    # scriptsフォルダの中身を列挙し、.py拡張子を除いて返す
    with resources.path("pya_tools.scripts", "") as scripts_path:
        scripts_dir = str(scripts_path)
        files = os.listdir(scripts_dir)
        scripts = [f[:-3] for f in files if f.endswith(".py") and f != "__init__.py"]
    return scripts
  

def copy_config_dir(pya_name: str, dest_dir: Path):
  try:
    config_pkg = f"pya_tools.config.{pya_name}"
    with resources.as_file(resources.files(config_pkg)) as src:
      if not src.is_dir():
        print(f"Error: config directory not found for '{pya_name}'")
        return
    
      dest_dir.mkdir(parents=True, exist_ok=True)
      for item in src.iterdir():
        if item.is_file():
          shutil.copy(item, dest_dir / item.name)
          
      print(f"Config for '{pya_name}' copied to: {dest_dir}")


  except ModuleNotFoundError:
    print(f"No config found for '{pya_name}'")
  except Exception as e:
    print(f"Error copying config: {e}")


def main():
  available = list_available_scripts()  
  parser = argparse.ArgumentParser(description="Run a pip-installed klayout pya script")

  # 独自オプション
  parser.add_argument(
    "--pya",
    dest="pya",
    type=str,
    required=True,
    help=f"Script name inside scripts (available: {', '.join(available)})"
  )

  parser.add_argument("--copy-config",
    action="store_true",
    help="Copy config for the given --pya"
                       ) 
  # -hはargparseが処理
  
  # 残りの全ての引数（KLayoutにそのまま渡す）
  args, unknown_args = parser.parse_known_args()

  # pyaスクリプト名を取得
  script_name = args.pya + ".py"

  # copy config
  if args.copy_config:
    if not args.pya:
      print("[ERR]: --pya must be specified with --copy-config")
      return
  
    dest = Path.cwd() / f"config.{args.pya}"
    #if dest.exists():
    #  shutil.rmtree(dest)
    copy_config_dir(args.pya, dest)

    # message to user
    if args.pya == "pya_gds2lef":
      print("\nSample GDS file:")
      print("  config.pya_gds2lef/sg13g2_stdcell.gds\n")
      print("!! Please get GDS file from github and copy to upper path for testing:")
      print("!! --rd in_gds=config.pya_gds2lef/sg13g2_stdcell.gds")
    
    
    
    return  
  
  # do klayout
  try:
    with resources.path("pya_tools.scripts", script_name) as script_path:
      cmd = ["klayout", "-r", str(script_path)] + unknown_args

      print(f"Running: {' '.join(cmd)}")  # デバッグ表示

      subprocess.run(cmd, check=True)
  except FileNotFoundError:
    print(f"Script '{script_name}' not found in pya_tools.scripts.")
    sys.exit(1)
  except subprocess.CalledProcessError as e:
    print("KLayout returned non-zero exit status:", e.returncode)
    sys.exit(e.returncode)
        

if __name__ == "__main__":
    main()
        
