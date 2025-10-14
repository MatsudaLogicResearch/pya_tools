# PROJECT
python scripts using pya(Python API) for Klayout.

# LICENSE
Copyright (C) 2025 LogicResearch K.K. (Author: MATSUDA Masahiro)

This project is licensed under the MIT License.
Please see the LICENSE file for details.

# TOOLS
## pya_flatspice

### description
flatten spice netlist.

### usage
```bash
klayout -b -r pya_flatspice.py \ 
-rd ifile=xxx \ 
-rd ofile=yyyy \ 
-rd top=top_cell
```

| オプション名  | 説明                      | 必須 | 備考                  |
| ------- | ----------------------- | -- | ------------------- |
| `ifile` | 入力ファイル名（例: GDSやLEFファイル） | Y | 処理対象となるファイルを指定します   |
| `ofile` | 出力ファイル名                 | Y | 結果を書き出すファイル名を指定します  |
| `top`   | トップセル名                  | Y | レイアウト内のトップセル名を指定します |



## pya_gds2lef

### description
generate tech.lef / macro.lef from jsonc/GDS files.

### usage
```bash
klayout -b -r pya_gds2lef.py \ 
-rd in_jsonc_tech=in_tech.jsonc \ 
-rd in_jsonc_macro=in_macro.jsonc \ 
-rd in_jsonc_gdslayer=in_gdslayer.jsonc \ 
-rd in_gds=sg13g2_stdcell.gds \ 
-rd out_lef_macro=out_macro.lef\ 
(-rd out_lef_tech=out_tech.lef)
```

| オプション名              | 説明                            | 必須 | 備考                   |
| ------------------- | ----------------------------- | -- | -------------------- |
| `in_jsonc_tech`     | テクノロジー情報を含むJSONCファイルのパス       | Y | レイヤーや製造情報などを含む(ex: target/in_tech.jsonc)       |
| `in_jsonc_macro`    | マクロ情報を含むJSONCファイルのパス          | Y | 標準セルなどのマクロ情報(ex: target/in_macro.jsonc)         |
| `in_jsonc_gdslayer` | GDSレイヤーマッピング情報を含むJSONCファイルのパス | Y | GDSのレイヤー番号と意味の対応付け(ex: target/in_gdslayer.jsonc)   |
| `in_gds`            | 入力GDSファイル名                    | Y | 変換対象のGDSレイアウトファイル    |
| `out_lef_macro`     | 出力するLEFのマクロファイル名              | Y | 標準セルなどのLEFマクロ情報の出力先  |
| `out_lef_tech`      | 出力するLEFのテクノロジーファイル名           | N | LEF形式のテクノロジーファイルの出力先(out_lef_macroと同じファイル名を指定可能) |

### check
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
