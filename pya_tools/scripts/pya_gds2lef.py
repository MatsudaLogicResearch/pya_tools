#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#===================================================================
# This file is associated with the pya_toos project.
# Copyright (C) 2025 Logic-Research K.K. (Author: MATSUDA Masahiro)
# 
# This script file is licensed under the MIT License.
#===================================================================

#import jsoncomment  # json parser
import json  # json parser
import pya  # for KLayout

import re
import os,sys,argparse

from collections import OrderedDict
from  typing import Any,Dict

# ------------------------
# functions
# ------------------------
def get_unused_layer_info(layout:pya.Layout, start_layer:int=1000, start_datatype:int=0) -> pya.LayerInfo:
    """layout内で未使用の layer/datatype を返す"""
    
    used = set()
    for i in range(layout.layers()):
        li = layout.get_info(i)
        used.add((li.layer, li.datatype))
    
    for l in range(start_layer, 4096):
        for d in range(start_datatype, 16):
            if (l, d) not in used:
                return pya.LayerInfo(l, d)
    
    raise RuntimeError("No available LayerInfo found")

def remove_json_comments(text:str) -> str:
    """
    JSON文字列から //, #, /* */ コメントを安全に削除
    """
    def replacer(match):
        s = match.group(0)
        if s.startswith(('"', "'")):
            return s  # 文字列はそのまま
        return ''     # コメントは空に

    # 正規表現：文字列またはコメント
    pattern = r"""
        ("(?:\\.|[^"\\])*"         # ダブルクォート文字列
        | '(?:\\.|[^'\\])*')       # シングルクォート文字列
        | (//.*?$)                 # C++スタイルコメント
        | (/\*.*?\*/)              # Cスタイルブロックコメント
    """

    regex = re.compile(pattern, re.MULTILINE | re.DOTALL | re.VERBOSE)
    return regex.sub(replacer, text)

def load_json_with_comments(path:str) -> Dict[str,Any]:
    """
    commentありのJSONファイルを読み込む
    """
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()
    cleaned = remove_json_comments(text=raw)
    #print(cleaned)
    return json.loads(cleaned)
  
def list2d_to_str(dt:list) -> str:
  """
  jsonファイル中のvalue(値/1次リスト/2次リスト)にあわせ、文字列変換
  ex) [-1,-2,-3]  ---> (-1 -2 -3)
  """
    
  # 各内側リストを "1 2" のようにスペース区切り文字列に変換し、丸括弧で囲む
  inner_strs = ["( " + " ".join(str(x) for x in row) + " )" for row in dt]
  # それらをスペース区切りでつなぎ、さらに外側を丸括弧で囲む
  return "( " + " ".join(inner_strs) + " ) "


def conv_dict2lef(param:dict, hier:int=0) -> list[str]:
  """
  辞書に格納されたパラメータ値を文字列に変換
    keyは、パラメータ名として"_"で分割
    valueは、値として扱う

    ex)  "A_B_C":[,[2.1,2.2],3]  --->  A B (2.1 2.2) C 3 
  """
  
  lines=[]
  for k,v in param.items():
    #print(f"  [DBG] key={k} ,value={v}")
      
    #--- val is always list
    vals = v if isinstance(v, list) else [v]
    #--- split key
    keys=k.split("_")

    len_keys =len(keys)
    len_vals =len(vals)
    if len_keys > len_vals:
      print(f'[ERR] length of value is fewwer than key({len_keys}/{len_vals}). key={k}, val={v}')
      sys.exit()
      
    #--
    line="  "*hier
    for ii in range(len_keys):
      # key
      line += f'{keys[ii].upper()} '

      # value
      vv = vals if (len_keys==1) else vals[ii] if isinstance(vals[ii], list) else [vals[ii]]

      # convert
      if (len(vv)==1):
        if vv[0] is None:
          pass
        #elif isinstance(vv[0],str):
        #  line += f'"{vv[0]}" '
        else:
          line += f'{vv[0]} '
      elif isinstance(vv[0],list):
        line += list2d_to_str(vv) + " "
      else:
        line +=" ".join([str(v) for v in vv]) + " "

    #
    line+=";"
    
    #--
    lines .append(line)
  
  return lines

def to_manhattan_region(region: pya.Region) -> pya.Region:
  """
  regionをmanhattan(矩形の多角形)へ変換
  備考) LEFのRECT図形として出力するため
  """
    
  manh_region = pya.Region()

  #-- polygonだけのはずなので、polygonに対してmanhattan処理を行う
  for polygon in region.merged().each():
    try:
      manh_poly = to_manhattan_polygon(polygon)
      manh_region.insert(manh_poly)
    except Exception as e:
      print(f"[ERROR] polygon skipped due to: {e}")
  
  return manh_region

# ------------------------
# polygon to manhattan
# ------------------------
def to_manhattan_polygon(polygon: pya.Polygon) -> pya.Polygon:
  """
  polygonをmanhattan(矩形の多角形)へ変換
  備考) LEFのRECT図形として出力するため
  """
  
  points = [p for p in polygon.to_simple_polygon().each_point()]
  manhattan_points = []

  for i in range(len(points)):
    p0 = points[i]
    p1 = points[(i + 1) % len(points)]; #--最後は0につなぐ

    # 開始点を追加
    manhattan_points.append(p0)

    # 直線移動の場合は次へ
    if (p0.x == p1.x) or  (p0.y == p1.y):
      continue
    
    # 斜め移動があれば、内接を移動(移動点を追加)
    pa = pya.Point(p0.x, p1.y)
    pb = pya.Point(p1.x, p0.y)

    if   polygon.inside(pa):
      manhattan_points.append(pa)
    elif polygon.inside(pb):
      manhattan_points.append(pb)
    else :
      print(f"[ERROR] illegal positon({p0} - {p1})")
      sys.exit()
      
  #
  return pya.Polygon(manhattan_points)

def split_manhattan_region_to_rects(region: pya.Region) -> list:
  """
  入力 region 内の各マンハッタンポリゴンを矩形に分割し、すべての矩形をリストで返す
  """
  rects = []
  for polygon in region.each():
    rect_list = split_manhattan_polygon_to_rects(polygon)
    rects.extend(rect_list)
  return rects

def split_manhattan_polygon_to_rects(polygon: pya.Polygon) -> list:
  """
  入力 polygonを矩形に分割し、すべての矩形をリストで返す
  """

  def polygon_to_point_list(polygon):
    return [p for p in polygon.to_simple_polygon().each_point()]

  def find_top_y(points, x, y):
    # 指定された (x, y) に対し、直上にある点を探す
    candidates = [p for p in points if p.x == x and p.y > y]
    if not candidates:
      return None
  
    return min(candidates, key=lambda p: p.y)

  def extract_rectangle(points):
    # 0. 終了条件：矩形（4点）になったらBoxに変換して返す
    if len(points) == 4:
      xs = [p.x for p in points]
      ys = [p.y for p in points]
      return [pya.Box(min(xs), min(ys), max(xs), max(ys))]

    # 1. 最も下のYを取得
    y0 = min(p.y for p in points)

    # 2. y0を持つ点の中で最も左のX
    y0_points = [p for p in points if p.y == y0]
    x0 = min(p.x for p in y0_points)
    pb_l = pya.Point(x0, y0)

    # 3. 同じY0の点の中で最も右のX
    x1 = max(p.x for p in y0_points)
    pb_r = pya.Point(x1, y0)

    # 4. 左右の直上の点（PH_L, PH_R）を取得
    ph_l = find_top_y(points, x0, y0)
    ph_r = find_top_y(points, x1, y0)

    if not ph_l or not ph_r:
      print(f"[ERROR] upper point(PH_L/PH_R) are not exist in manhattan-polygon.")
      sys.exit()
      #raise RuntimeError("PH_L or PH_R not found")

    y1 = ph_l.y
    y2 = ph_r.y

    # 5. PB_L ~ PH_L, PB_R ~ PH_R で囲まれた矩形内に中間のY座標があるか探す
    min_y = min(y1, y2)
    inner_points = [p for p in points if p.x > x0 and p.x < x1 and p.y > y0 and p.y < min_y]

    if inner_points:
      y3 = min(p.y for p in inner_points)  # 最も近い内包Y
      rect = pya.Box(x0, y0, x1, y3)
    else:
      rect = pya.Box(x0, y0, x1, min_y)

    return rect

  # 開始：Regionとして差分処理を行う
  remaining_region = pya.Region(polygon)
  rects = []

  while not remaining_region.is_empty():
    # 最初のポリゴンだけ使う（複数ある場合はループで回る）
    first_poly = next(remaining_region.each())

    points = polygon_to_point_list(first_poly)
    rect = extract_rectangle(points)
    if isinstance(rect, list):
      rect_box = rect[0]
    else:
      rect_box = rect

    rects.append(rect_box)
    #print(f"type2={type(rect_box)}, type3={type(rects)}")

    # RECT を Region として切り出し、差分にして残す
    rect_region = pya.Region(rect_box)
    remaining_region = remaining_region - rect_region

  return rects

# ------------------------
# search pin region
# ------------------------
def get_pin_rects(cell: pya.Cell, macro_dict=None) -> list:

  pin_list=[]
  if macro_dict is None:
    print(f"[ERROR] macro_dict is Empty!")
    sys.exit()
  
  #-- search TEXT on All Metal.
  for layer_name,v in macro_dict["METAL_DRAW_TEXT_LAYER"].items():
    (layer_text_num,layer_text_datatype) = v["TEXT"]
    (layer_draw_num,layer_draw_datatype) = v["DRAW"]
    
    layer_text_info=ly.layer(layer_text_num, layer_text_datatype)
    layer_draw_info=ly.layer(layer_draw_num, layer_draw_datatype)

    connect(layer_text_info, layer_draw_info)

    
    #-- search draw region by LAYER
    metal_region = pya.Region(cell.shapes(layer_draw_info)).merged()
    if metal_region.is_empty():
      continue

    #-- text on same LAYER
    for text_shape in cell.shapes(layer_text_info).each():

      #-- is text?
      if not text_shape.is_text():
        continue
      text_name=text_shape.text.string

      #-- check if text is inside of shape?
      text_point=text_shape.text.trans.disp
      pad_shape=next((p for p in metal_region.each() if p.bbox().contains(text_point) and p.inside(text_point)),None)
      if pad_shape is None:
        continue

      #-- convert from polygon to manhattan
      pad_manhattan=to_manhattan_polygon(polygon=pad_shape)
      
      #-- convert from manhattan-polygon to list[box]
      pad_rects = split_manhattan_polygon_to_rects(polygon=pya.Polygon(pad_manhattan))

      if pad_rects is None:
        print(f"[ERROR] TEXT/DRAW are not overlap. text={text_name}, layer={layer_name}")
      else:
        pin_list.append((text_name, layer_name, pad_rects))

  #--
  if len(pin_list)<1:
    print(f"[ERR] no pad exist.")
    sys.exit()

  return pin_list


def write_lef_tech(tech_dict:dict(), tlef:str, mlef:str):
  """
  write tech lef
  """

  outlines1 = []
  outlines2 = []

  print(f"[INF] writing tech.lef")
  
  ## info1
  #--------------------------------------
  id="info1"
  if id in tech_dict.keys():
    print(f'  [INF] detect {id} blocks')
    lines=[]
    lines.extend(conv_dict2lef(param=tech_dict[id], hier=0))
    lines.append(f'')
    
    outlines1.extend(lines)

  ## units
  #--------------------------------------
  id="units"
  if id in tech_dict.keys():
    print(f'  [INF] detect {id} blocks')
    lines=[]
    lines.append(f'UNITS')
    lines.extend(conv_dict2lef(param=tech_dict[id], hier=1))
    lines.append(f'END UNITS')
    lines.append(f'')
    
    outlines2.extend(lines)

  ## info2
  #--------------------------------------
  id="info2"
  if id in tech_dict.keys():
    print(f'  [INF] detect {id} blocks')
    lines=[]
    lines.extend(conv_dict2lef(param=tech_dict[id], hier=0))
    lines.append(f'')
    
    outlines2.extend(lines)


  ## layer_masterslice
  #--------------------------------------
  id="layer_masterslice"
  if id in tech_dict.keys():
    print(f'  [INF] detect {id} blocks')
    for n,vv in tech_dict[id].items():
      lines=[]
      lines.append(f'LAYER {n}')
      lines.append(f'  TYPE MASTERSLICE ;')
      if vv is not None:
        lines.extend(conv_dict2lef(param=vv, hier=1))
      lines.append(f'END {n}')
      lines.append(f'')
      #
      outlines2.extend(lines)

  ## layer_cut
  #--------------------------------------
  id="layer_cut"
  if id in tech_dict.keys():
    print(f'  [INF] detect {id} blocks')
    for n,vv in tech_dict[id].items():
      lines=[]
      lines.append(f'LAYER {n}')
      lines.append(f'  TYPE CUT ;')
      if vv is not None:
        lines.extend(conv_dict2lef(param=vv, hier=1))
      lines.append(f'END {n}')
      lines.append(f'')
      #
      outlines2.extend(lines)

  ## layer_routing
  #--------------------------------------
  id="layer_routing"
  if id in tech_dict.keys():
    print(f'  [INF] detect {id} blocks')
    for n,vv in tech_dict[id].items():
      lines=[]
      lines.append(f'LAYER {n}')
      lines.append(f'  TYPE ROUTING ;')
      if vv is not None:
        lines.extend(conv_dict2lef(param=vv, hier=1))
      lines.append(f'END {n}')
      lines.append(f'')
      #
      outlines2.extend(lines)

  ## via_default
  #--------------------------------------
  id="via_default"
  if id in tech_dict.keys():
    print(f'  [INF] detect {id} blocks')
    for n,vv in tech_dict[id].items():
      lines=[]
      lines.append(f'VIA {n} DEFAULT')
      for kkk,vvv in vv.items():
        if kkk in ["top", "bottom", "via"]:
          #print(vvv)
          lines.extend(conv_dict2lef(param=vvv, hier=1))
        else:
          #print({kkk:vvv})
          lines.extend(conv_dict2lef(param={kkk:vvv}, hier=1))
      lines.append(f'END {n}')
      lines.append(f'')
      #
      outlines2.extend(lines)
      
  ## viarule_generate
  #--------------------------------------
  id="viarule_generate"
  if id in tech_dict.keys():
    print(f'  [INF] detect {id} blocks')
    for n,vv in tech_dict[id].items():
      lines=[]
      lines.append(f'VIARULE {n} GENERATE')
      for kkk,vvv in vv.items():
        if kkk in ["top", "bottom", "via"]:
          #print(vvv)
          lines.extend(conv_dict2lef(param=vvv, hier=1))
        else:
          #print({kkk:vvv})
          lines.extend(conv_dict2lef(param={kkk:vvv}, hier=1))
      lines.append(f'END {n}')
      lines.append(f'')
      #
      outlines2.extend(lines)


  #--------------------------------------
  # write to file
  if tlef:
    with open(tlef, 'w') as f:
      s = "\n".join(outlines1) + "\n"
      f.write(s)

      s = "\n".join(outlines2) + "\n"
      f.write(s)

  #--------------------------------------
  # tech.lef
  #print(f"mlef={mlef}, tlef={tlef}")
  
  if tlef:
    if tlef != mlef:
      ##- write to tlef
      with open(tlef, 'w') as f:
        s = "\n".join(outlines1) + "\n"
        f.write(s)

        s = "\n".join(outlines2) + "\n"
        f.write(s)

      ##- write to mlef
      with open(mlef, 'w') as f:
        s = "\n".join(outlines1) + "\n"
        f.write(s)
        
    else:
      ##- write to mlef
      with open(mlef, 'w') as f:
        s = "\n".join(outlines1) + "\n"
        f.write(s)

        s = "\n".join(outlines2) + "\n"
        f.write(s)
        
      
  else:
    with open(mlef, 'w') as f:
      s = "\n".join(outlines1) + "\n"
      f.write(s)

def write_lef_macro_site(macro_dict=dict(), mlef=str):
  """
  write macro lef(site)
  """
    
  outlines = []
  ## site
  #--------------------------------------
  id="SITE"
  if id in macro_dict.keys():
    print(f'  [INF] detect {id} blocks')
    for n,vv in macro_dict[id].items():
      lines=[]
      lines.append(f'SITE {n}')
      if vv is not None:
        lines.extend(conv_dict2lef(param=vv, hier=1))
      lines.append(f'END {n}')
      lines.append(f'')
      #
      outlines.extend(lines)
      

  #--------------------------------------
  # macro.lef
  with open(mlef, 'a') as f:
    s = "\n".join(outlines) + "\n"
    f.write(s)


def trace_region(tech:pya.NetTracerConnectivity, layout:pya.Layout, layout_cell:pya.Cell, start_point:pya.DVector, start_layer_index:int, start_port_name:str, stop_layer_index:int) ->pya.Region:

  """
  tech(connectivity設定済)の接続条件で、layout(GDS)中の特定セル(layout_cell)に対して、
  start_point/start_layer_indexの地点から、stop_layer_indexまでの接続情報を持ったregionを返す。
  """
    
  merged_region=pya.Region()
  #index_metal_layer  = layout.layer( gdslayer_dict["GDS_LAYER_INFO"][start])

  tracer = pya.NetTracer()
  #start_point = sorted_port_layer_pos[port_name][metal_name]
  net = tracer.trace(tech, layout, layout_cell, start_point, start_layer_index)

  
  if net is None:
    return merged_region

  for e in net.each_element():

    #-- skeip
    #stop_layer_info=layout.get_info(stop_layer_index)
    #e_layer_info   =layout.get_info(e.layer())
    target_layer_index=e.layer()
    
    #print(f"stop={stop_layer_index}, target={target_layer_index}")
    
    if target_layer_index != stop_layer_index:
      continue
  
    #-- get region
    shape = e.shape()
    trans = e.trans()
      
    if shape.is_box():
      poly = shape.box.transformed(trans)
    elif shape.is_polygon():
      poly = shape.polygon.transformed(trans)
    elif shape.is_path():
      poly = shape.path.polygon.transformed(trans)
    else:
      #print("[WRN]: Unsupported shape type")
      continue

    #--
    merged_region.insert(pya.Region(poly))
        
  ##
  if merged_region:
    merged_region = merged_region.merged()

  return(merged_region)


# ------------------------
# klayout(main)
# ------------------------
#in_gds="in_sample.gds"
#in_jsonc_gdslayer="in_gdslayer.jsonc"
#in_jsonc_tech="in_tech.jsonc"
#in_jsonc_macro="in_macro.jsonc"
#out_lef_tech="tech.lef"
#out_lef_macro="macro.lef"

#-- set inital input/output file
if 'in_jsonc_gdslayer' not in globals():
  in_jsonc_gdslayer="config.pya_gds2lef/in_gdslayer.jsonc"
if 'in_jsonc_tech' not in globals():
  in_jsonc_tech    ="config.pya_gds2lef/in_tech.jsonc"
if 'in_jsonc_macro' not in globals():
  in_jsonc_macro   ="config.pya_gds2lef/in_macro.jsonc"
if 'in_gds' not in globals():
  in_gds           ="config.pya_gds2lef/sg13g2_stdcell.gds"

if 'out_lef_macro' not in globals():
  out_lef_macro    ="out_macro.lef"
  
#check var & file
for f in [in_gds, in_jsonc_gdslayer,  in_jsonc_tech, in_jsonc_macro]:
  if not os.path.isfile(f):
    print(f"[ERROR]: Input file '{f}' does not exist.", file=sys.stderr)
    sys.exit(1)

#-- print parameter & read json files
if True:
  print(f"[INF]: in_jsonc_tech    ={in_jsonc_tech}")
  tech_dict=load_json_with_comments(in_jsonc_tech)

  print(f"[INF]: in_jsonc_macro   ={in_jsonc_macro}")
  macro_dict=load_json_with_comments(in_jsonc_macro)

  print(f"[INF]: in_jsonc_gdslayer={in_jsonc_gdslayer}")
  gdslayer_dict=load_json_with_comments(in_jsonc_gdslayer)

  print(f"[INF]: in_gds           ={in_gds}")
  
if 'out_lef_tech' not in globals():
  out_lef_tech = None

print(f"[INF]: out_lef_macro    ={out_lef_macro}")
if out_lef_tech:
  print(f"[INF]: out_lef_tech     ={out_lef_tech}")


#-- write tech lef
write_lef_tech (tech_dict=tech_dict, tlef=out_lef_tech, mlef=out_lef_macro)

#-- read gds & flatten
layout = pya.Layout()
layout.read(in_gds)

for c in layout.each_cell():
  for i in c.each_inst():
    i.flatten()

#-- get parameter from GDS    
top_cells=layout.top_cells()
dbu_gds = layout.dbu

if not "BOUNDARY" in gdslayer_dict["GDS_LAYER_INFO"].keys():
  print(f"[ERROR] BOUNDARY_LAYER is not exist in {gdslayer}.")
  sys.exit()

#-- write macro lef(site)
write_lef_macro_site (macro_dict=macro_dict, mlef=out_lef_macro)

#-- write macro lef(macro)
for cell in top_cells:   #-- search all cell

  #-- if not defined in"MACRO", skip
  if not cell.name in macro_dict["MACRO"].keys():
    print(f"[INF]: skipping {cell.name}")
    continue;

  #-- 
  macro_name  = cell.name
  macro_info  = macro_dict["MACRO"][macro_name]
  layout_cell = next((c for c in layout.top_cells() if c.name == macro_name), None)
  
  print(f"[INF] target macro={macro_name}")

  ####################################################################
  #--get PORT positon in MACRO
  
  port_layer_pos={}
  for metal_name, text_name in gdslayer_dict["GDS_LAYER_CONNECT_TEXT"].items():
    index_text_layer  = layout.layer( gdslayer_dict["GDS_LAYER_INFO"][text_name])
    for shape in layout_cell.shapes(index_text_layer):
      if not shape.is_text():
        continue

      port_name = shape.text.string
      port_point= shape.text.trans.disp

      if port_name not in port_layer_pos:
        port_layer_pos[port_name] = {}
        
      port_layer_pos[port_name][metal_name]=port_point

  if not port_layer_pos:
    print(f"[ERR] not Text is exist for All PORT.")
    sys.exit()

  sorted_port_layer_pos = OrderedDict()
  for port_name in sorted(port_layer_pos.keys()):
    sorted_port_layer_pos[port_name] = OrderedDict()
    for metal_name in sorted(port_layer_pos[port_name].keys()):
      sorted_port_layer_pos[port_name][metal_name] = port_layer_pos[port_name][metal_name]
    
  #print(f"[DBG]: port_layer_pos")

  ####################################################################
  ##-- create new layer for signal-connection

  gds_regions={}
  symbol_name_val_index={}
  ### - get reagion from GDS
  for ly_name,ly_num_type in gdslayer_dict["GDS_LAYER_INFO"].items():
    layer_info  = pya.LayerInfo(ly_num_type[0], ly_num_type[1])
    layer_index = layout.find_layer(layer_info)

    if layer_index is None:
      continue
  
    region=pya.Region()
    region.insert(cell.shapes(layer_index))
    gds_regions[ly_name]=region

    symbol_name_val_index[ly_name]=[f"{ly_num_type[0]}/{ly_num_type[1]}",layer_index]

    #print(f"[DBG]: name={ly_name}, index={layer_index}")
    
  ### - create reagion, write back to cell
  for ly_name,expr in gdslayer_dict["GDS_LAYER_CREATE"].items():
    new_region=eval(expr)
    
    new_layer_info  = get_unused_layer_info(layout)
    new_layer_index = layout.insert_layer(new_layer_info)
    
    new_region.insert_into(layout, cell.cell_index(), new_layer_index)
    gds_regions[ly_name]=new_region

    symbol_name_val_index[ly_name]=[f"{new_layer_info.layer}/{new_layer_info.datatype}",new_layer_index]

    #print(f"[DBG]: name={ly_name}, index={new_layer_index}")
    
  ####################################################################
  #--get PORT AREA

  ##-- create symbol
  tech4port = pya.NetTracerConnectivity()
  for symbol_name, symbol_val_index in symbol_name_val_index.items():
    tech4port.symbol(symbol_name, symbol_val_index[0])

  ##-- connect symbols for TEXT/MEAL
  for metal_name, text_name in gdslayer_dict["GDS_LAYER_CONNECT_TEXT"].items():
    tech4port.connection(metal_name, text_name)
  
  ##-- trace from PORT to Metal
  port_region={}
  for port_name in sorted_port_layer_pos.keys():
    for metal_name in sorted_port_layer_pos[port_name].keys():

      start_point       = sorted_port_layer_pos[port_name][metal_name]
      #start_layer_index = layout.layer( gdslayer_dict["GDS_LAYER_INFO"][metal_name])
      
      layer_val_index   = symbol_name_val_index[metal_name]
      start_layer_index = layer_val_index[1]
      
      stop_layer_index  = start_layer_index
      
      ###-- get PORT region
      region = trace_region(tech4port, layout, layout_cell, start_point, start_layer_index, port_name, stop_layer_index)
      if region:
        if port_name not in port_region:
          port_region[port_name]={}

        ####- manhattanize
        #manh_region =to_manhattan_region(region)
        manh_region =region

        ###- save
        port_region[port_name][metal_name] = manh_region
        #print(f"[DBG]: set port_region for {port_name}")
        
  ####################################################################
  #--get GATE AREA
  
  ##-- connect symbols
  for pair in gdslayer_dict["GDS_LAYER_CONNECT_GATE_DIFF"]:
    layer1 = pair[0]
    layer2 = pair[1]
    tech4port.connection(layer1, layer2)
  
  ##-- trace from PORT to GATE/DIFF
  gate_area={}
  diff_area={}
  for port_name in sorted_port_layer_pos.keys():
    for metal_name in sorted_port_layer_pos[port_name].keys():

      start_point       = sorted_port_layer_pos[port_name][metal_name]
      layer_val_index   = symbol_name_val_index[metal_name]
      start_layer_index = layer_val_index[1]

      ###-- get GATE region & area
      layer_val_index   = symbol_name_val_index["GATE"]
      stop_layer_index  = layer_val_index[1]
      
      region = trace_region(tech4port, layout, layout_cell, start_point, start_layer_index, port_name, stop_layer_index)
      if region:
        if port_name not in gate_area:
          gate_area[port_name]={}
          
        gate_area[port_name][metal_name] = region.area() * (dbu_gds * dbu_gds)

      ###-- get DIFF region & area
      layer_val_index   = symbol_name_val_index["DIFF"]
      stop_layer_index  = layer_val_index[1]
      
      region = trace_region(tech4port, layout, layout_cell, start_point, start_layer_index, port_name, stop_layer_index)
      if region:
        if port_name not in diff_area:
          diff_area[port_name]={}
          
        diff_area[port_name][metal_name] = region.area() * (dbu_gds * dbu_gds)

  #-- write lef
  outlines = []
  outlines.append(f"MACRO {macro_name}")
  outlines.append(f"  ORIGIN 0 0 ;")
  outlines.append(f"  FOREIGN {macro_name} 0 0 ;")
  
  lines=[]
  for kk,vv in macro_info.items():
    if kk=="PIN":
      continue
    if vv is not None:
      lines.extend(conv_dict2lef(param={kk:vv}, hier=1))
  outlines.extend(lines)

  #--- othres
  layer_boundary_num      = gdslayer_dict["GDS_LAYER_INFO"]["BOUNDARY"][0]
  layer_boundary_datatype = gdslayer_dict["GDS_LAYER_INFO"]["BOUNDARY"][1]
  layer_boundary_info=layout.layer(layer_boundary_num, layer_boundary_datatype)
  boundary_region = pya.Region(cell.shapes(layer_boundary_info)).merged()
  if boundary_region.is_empty():
    print(f"[ERR]: boundary layer is not exist in {macro_name}.")
    sys.exit()
    
  b_box=boundary_region.bbox()
  w=b_box.width()  * dbu_gds
  h=b_box.height() * dbu_gds
  
  outlines.append(f"  SIZE {w:.3f} BY {h:.3f} ;")
  
  #--- PIN
  if not "PIN" in macro_info.keys():
    print(f"[ERROR] PIN is not defined in {macro_json}")
    sys.exit()

  pin_info_dict=macro_info["PIN"]
  for pin_name,pin_params in pin_info_dict.items():

    #-- check if pin is exist in GDS
    #print (port_region)
    if pin_name not in port_region.keys():
      print(f"[ERR] {pin_name} is not exist in GDS.")
      sys.exit()
      
    #-- write data  for PIN
    layer_region=port_region[pin_name]
    outlines.append(f"  PIN {pin_name}")
    
    #-- write data from macro.json
    lines=[]
    for kk,vv in pin_params.items():
      if vv is not None:
        lines.extend(conv_dict2lef(param={kk:vv}, hier=2))
    outlines.extend(lines)
      
    #-- write data for ANTENNAGATEAREA
    if pin_name in gate_area.keys():
      for layer in gate_area[pin_name].keys():
        area = gate_area[pin_name][layer]
        outlines.append(f"    ANTENNAGATEAREA {area:.3f} LAYER {layer} ;")
    
    #-- write data for ANTENNADIFFAREA
    if pin_name in diff_area.keys():
      for layer in diff_area[pin_name].keys():
        area = diff_area[pin_name][layer]
        outlines.append(f"    ANTENNADIFFAREA {area:.3f} LAYER {layer} ;")
    
    #-- write data for port
    outlines.append(f"    PORT")
    
    layers = sorted(layer_region.keys())
    for layer in layers:
      outlines.append(f"      LAYER {layer} ;")

      rects=split_manhattan_region_to_rects(layer_region[layer])
      for rect in rects:
        #print(f"[DEBUG] {pin_name} {rect}")
        x1 = rect.left    * dbu_gds
        y1 = rect.bottom  * dbu_gds
        x2 = rect.right   * dbu_gds
        y2 = rect.top     * dbu_gds
        
        outlines.append(f"        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
        
      outlines.append(f"    END"); #PORT
      
    outlines.append(f"  END {pin_name}"); #PIN
    
  #--- OBS
  lines_obs=[]
  #for metal_name, text_name in gdslayer_dict["GDS_LAYER_CONNECT_TEXT"].items():
  for obs_name in gdslayer_dict["GDS_LAYER_OBS"]:

    ##--- get OBS region
    index_obs_layer = layout.layer( gdslayer_dict["GDS_LAYER_INFO"][obs_name])
    obs_region      = pya.Region(cell.shapes(index_obs_layer))

    ##-- remove port region from obs_region
    if obs_region.is_empty():
      continue
  
    for port_name in port_region.keys():
      if obs_name in port_region[port_name].keys():
        obs_region = obs_region - port_region[port_name][obs_name]

    ##-- create RECT 
    if obs_region.is_empty():
      continue
  
    rects=split_manhattan_region_to_rects(obs_region)
      
    lines_obs.append(f"    LAYER {obs_name} ;")
    for rect in rects:
      #print(f"[DEBUG] {pin_name} {rect}")
      x1 = rect.left    * dbu_gds
      y1 = rect.bottom  * dbu_gds
      x2 = rect.right   * dbu_gds
      y2 = rect.top     * dbu_gds
      
      lines_obs.append(f"        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;")
        
  ##-- add lines_obs
  if len(lines_obs)>0:
    outlines.append(f"  OBS"); 
    outlines.extend(lines_obs); 
    outlines.append(f"  END"); 

  ##-- end of MACRO
  outlines.append(f"END {macro_name}"); #MACRO
  outlines.append(f"");


  #--------------------------------------
  # write to macro.lef
  if len(outlines)>0:
    with open(out_lef_macro, 'a') as f:
      s = "\n".join(outlines) + "\n"
      f.write(s)
    
## ------------------------
## 実行例（コマンドライン）
## ------------------------
#klayout -b -r pya_gds2lef.py -rd in_jsonc_tech=in_tech.jsonc -rd in_jsonc_macro=in_macro.jsonc -rd in_jsonc_gdslayer=in_gdslayer.jsonc -rd in_gds=sg13g2_stdcell.gds -rd out_lef_tech=out_tech.lef -rd out_lef_macro=out_macro.lef | grep -v skip

