# PROJECT
python scripts using pya(Python API) for Klayout.

# LICENSE
Copyright (C) 2025 LogicResearch K.K. (Author: MATSUDA Masahiro)

This project is licensed under the MIT License.
Please see the LICENSE file for details.

# INSTALL
```bash
pip install git+https://github.com/MatsudaLogicResearch/pya_tools.git
or
pip install git+https://github.com/MatsudaLogicResearch/pya_tools.git@v0.1.1
```

# USAGE

The pya-based scripts included in this package can be executed in **two ways**:

1. Running directly with KLayout (`-r` option)

You can run any script using KLayout’s `-r` option:

```bash
klayout -r path/to/pya_script.py
```

2. Running via this Python package (recommended)

After installing this package with pip, you can use the built-in runner tool to execute scripts without specifying full paths:


```bash
python -m pya_tools --pya <script_name> [Klayoyut options]
```

Examples:

*create config for pya_gds2lef*:

```bash
python -m pya_tools --pya pya_gds2lef --copy-config
```

*run pya_gds2lef*:

```bash
python -m pya_tools --pya pya_gds2lef -b \
--rd in_gds=sample.gds \
--rd in_jsonc_gdslayer=gdslayer.jsonc \
--rd in_jsonc_macro=macro.jsonc \
--rd in_jsonc_tech=tech.jsonc  \
--rd out_lef_tech=tech.lef \
--rd out_lef_macro=macro.lef
```

* run pya_flatspice*:
```bash
python -m pya_tools --pya flatspice -b \
--rd ifile=input.spice \
--rd ofile=output.spice \
--rd top=top_cell
```

## pya_flatspice

### description
flatten SPICe netlist.

### usage with pythom -m
| オプション名  | 説明                      | 必須 | 備考                  |
| ------- | ----------------------- | -- | ------------------- |
| `--pya pya_flatspice`      | pya_flatspiceスクリプトをklayoutへ渡す                   | Y | |
| `--rd ifile=` | 入力ファイル名（例: GDSやLEFファイル） | Y | 処理対象となるファイルを指定します   |
| `--rd ofile=` | 出力ファイル名                 | Y | 結果を書き出すファイル名を指定します  |
| `--rd top=`   | トップセル名                  | Y | レイアウト内のトップセル名を指定します |



## pya_gds2lef

### description
generate tech.lef / macro.lef from jsonc/GDS files.
support only ANTENNAGATEAREA/ANTENNADIFFAREA.

### usage with python -m 

| オプション名              | 説明                            | 必須 | 備考                   |
| ------------------- | ----------------------------- | -- | -------------------- |
| `--pya pya_gds2lef`      | pya_gds2lefスクリプトをklayoutへ渡す                   | Y | |
| `--copy_config`          | コンフィグファイルの雛形を生成                   | Y | ./config.pya_gds2lef配下に生成     |
| `--rd in_jsonc_tech=`     | テクノロジー情報を含むJSONCファイルのパス       | Y | レイヤーや製造情報などを含む(ex: target/in_tech.jsonc)       |
| `--rd in_jsonc_macro=`    | マクロ情報を含むJSONCファイルのパス          | Y | 標準セルなどのマクロ情報(ex: target/in_macro.jsonc)         |
| `--rd in_jsonc_gdslayer=` | GDSレイヤーマッピング情報を含むJSONCファイルのパス | Y | GDSのレイヤー番号と意味の対応付け(ex: target/in_gdslayer.jsonc)   |
| `--rd in_gds=`            | 入力GDSファイル名                    | Y | 変換対象のGDSレイアウトファイル    |
| `--rd out_lef_macro=`     | 出力するLEFのマクロファイル名              | Y | 標準セルなどのLEFマクロ情報の出力先  |
| `-rd out_lef_tech=`      | 出力するLEFのテクノロジーファイル名           | N | LEF形式のテクノロジーファイルの出力先(out_lef_macroと同じファイル名を指定可能) |

### LEF file Validation(Optional)kcheck
yout can check the validity of your LEF files using "read_lef" command in OpenROAD.

```bash
openroad
>read_lef -tech out_tech.lef
>read_lef -library out_macro.lef
'''

If there are any syntax or consistency errors (e.g., missing layers or sites), OpenROAD will report them during the load.

Make sure that:
All layers used in out_macro.lef are defined in out_tech.lef.
All site names (e.g., CoreSite) are present in the tech LEF.
