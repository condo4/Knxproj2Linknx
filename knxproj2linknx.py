#!/usr/bin/env python

import zipfile, copy, sys, os
from lxml import etree

if len(sys.argv) < 3 or len(sys.argv) > 4:
    print("Export knxproj address group into linknx.xml file\n\t%s <knxfile> <linknx_source> [<linknx_output>]"%sys.argv[0])
    print("\t - If linknx_output is not set, print on stdout")
    print("\t - If linknx_output is - , modify linknx_source file (and generate linknx_source~ backup")
    exit(1)

DATATYPE = { \
    "DPT-1":      "1.001",
    "DPST-1-1":   "1.001",
    "DPST-1-3":   "1.003",
    "DPST-1-7":   "1.007",
    "DPST-1-8":   "1.008",
    "DPST-1-11":  "1.011",
    "DPST-3-7":   "3.007",
    "DPST-5-1":   "5.001",
    "DPT-5":      "5.xxx",
    "DPT-7":      "7.xxx",
    "DPST-9-1":   "9.001",
    "DPST-9-4":   "9.004",
    "DPST-9-6":   "9.006",
    "DPST-10-1":  "10.001",
    "DPST-11-1":  "11.001",
    "DPST-13-10": "13.xxx",
    "DPST-14-56": "14.xxx",
}


archive = zipfile.ZipFile(sys.argv[1], 'r')

# Extract Project file
projects = [ i for i in archive.filelist if "0.xml" in i.filename ]
if len(projects) != 1:
    print("Problem when loading file, can't find only one 0.xml; please send this file to fabien@kazoe.org")
    exit(-1)

f = archive.open(projects[0].filename)
xml = etree.fromstring(f.read())
namespaces = {"knx":"http://knx.org/xml/project/13" ,"xsd":"http://www.w3.org/2001/XMLSchema" ,"xsi":"http://www.w3.org/2001/XMLSchema-instance"}

GAs = xml.xpath("//knx:GroupAddresses/knx:GroupRanges", namespaces=namespaces)[0]
address_mask = [[0xFFFF], [0xF800, 0x07FF], [0xF800, 0x0700, 0x00FF]]

def ffs(x):
    """Returns the index, counting from 0, of the
    least significant set bit in `x`.
    """
    return (x&-x).bit_length()-1

objectlist = []

def processRange(rng, lvl, name = []):
    names = copy.copy(name)
    new_names = rng.attrib['Name'].title().replace("/","").split()
    for i in names:
        for s in i:
            if s in new_names:
                new_names.remove(s)
    names.append(new_names)
    if "GroupRange" in rng.tag:
        for r in rng.getchildren():
            processRange(r,lvl + 1, names)
    elif "GroupAddress" in rng.tag:
        idname = "_".join([  "".join(s) for s in names])
        if "DatapointType" in rng.attrib.keys():
            if not rng.attrib['DatapointType'] in DATATYPE.keys():
                print("ERROR: Unknown type " + rng.attrib['DatapointType'] + " for " + idname )
                datatype = None
            else:
                datatype = DATATYPE[rng.attrib['DatapointType']]
        else:
            datatype = None
        addr = int(rng.attrib['Address'])
        addrs = []
        for mask in address_mask[lvl]:
            addrs.append("%i"%((addr & mask) >> ffs(mask)))
        gad = "/".join(addrs)
        objectlist.append( (idname, datatype, gad) )
    else:
        print("TYPE %s NOT SUPPORTED"%rng.tag)

for rng in GAs.getchildren():
    processRange(rng, 0)


parser = etree.XMLParser(remove_blank_text=True)
linknx = etree.parse(sys.argv[2], parser)
parent = linknx.xpath("/config/objects")[0]

for src in objectlist:
    previous = linknx.xpath("//object[@id='%s']"%src[0])
    if len(previous) == 1:
        current_object = previous[0]
    else:
        current_object = etree.SubElement(parent,"object")
    if src[1]:
        current_object.attrib["type"] = src[1]
    current_object.attrib["id"] = src[0]
    current_object.attrib["gad"] = src[2]
    if "init" not in current_object.attrib.keys():
        current_object.attrib["init"] = "request"
    current_object.text = src[0]

if len(sys.argv) == 3:
    out = etree.tostring(linknx, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    for i in out.decode("utf-8").split("\n"):
        print(i)
    exit()

if sys.argv[3] == "-":
    os.rename(sys.argv[2], sys.argv[2] + "~")
    outfile = sys.argv[2]
else:
    outfile = sys.argv[3]

linknx.write(outfile, pretty_print=True, xml_declaration=True, encoding='UTF-8')
