from pathlib import Path
import importlib.metadata
from functools import lru_cache

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jinja2 import Template
import csv
import io
from typing import Dict, Any, List
from io import BytesIO
from openpyxl import Workbook

import uvicorn
import yaml
import toolbox

#pylint: disable = missing-function-docstring

# config
web_config = {}
with open("./config.yml", "r", encoding="utf-8") as fh:
    web_config = yaml.safe_load(fh)

# templating
templates = Jinja2Templates(directory="toolbox/web/templates")

app = FastAPI()
tb = toolbox.Toolbox()

# static files
dist = importlib.metadata.distribution("bootstrap")
static_path = Path(dist.locate_file("bootstrap/dist"))
app.mount("/bootstrap", StaticFiles(directory=str(static_path)), name="bootstrap")
app.mount("/static", StaticFiles(directory="toolbox/web/static"), name="static")

@lru_cache(maxsize=None)
def toolbox_wrapper(module_class, **kwargs):

    toolbox_module_obj = tb.init_module(module_class, kwargs)
    return toolbox_module_obj.run()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "web_config": web_config})

@app.get("/{toolgroup}/{tool}", response_class=HTMLResponse)
def get_tool(toolgroup:str, tool:str, request: Request):
    return render_tool(toolgroup, tool, request)

@app.get("/{toolgroup}/{tool}/run", response_class=HTMLResponse)
def run_tool(toolgroup:str, tool:str, request: Request):
    return render_tool(toolgroup, tool, request, True)

def render_tool(toolgroup:str, tool:str, request: Request, run: bool=False):

    toolgroup_config = web_config.get('groups', {}).get(toolgroup, None)
    if not toolgroup_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Toolgroup '{toolgroup}' not found.",
            "web_config": web_config
        }, status_code=404)

    tool_config = toolgroup_config.get('tools', {}).get(tool, None)
    if not tool_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Tool '{tool}' not found in toolgroup '{toolgroup}'.",
            "web_config": web_config
        }, status_code=404)

    toolbox_module = tb.load_module(tool_config.get('module'))
    toolbox_arguments = toolbox_module.Arguments.model_fields

    get_params = {}
    str_get_params = ""
    output_str = ""
    if run:
        get_params = dict(request.query_params)
        str_get_params = "&".join([f"{k}={v}" for k, v in get_params.items()])
        output_data = toolbox_wrapper(toolbox_module, **get_params)

        try:
            output_str = get_html_output(toolbox_module,output_data)
        except NotImplementedError:
            output_str = "No Output defined in Module"



    return templates.TemplateResponse("tool.html", {
        "request": request,
        "web_config": web_config,
        "path": (toolgroup, tool),
        "toolbox_arguments": toolbox_arguments,
        "toolgroup_config": toolgroup_config,
        "tool_config": tool_config,
        "toolbox_module": toolbox_module,
        "run": run,
        "params": get_params,
        "output_str": output_str,
        "str_get_params": str_get_params
    })



def get_html_output(module, output_data: Dict[str, Any]) -> str:
    """
    Gibt den HTML-Output zurück, der in der Web-GUI angezeigt werden soll.
    Falls OUTPUT_HTML_JINJA2 definiert ist, wird dieser genutzt (ggf. mit einem Jinja2-Renderer).
    Andernfalls wird ein generischer HTML-Code aus dem flachen Output erzeugt.
    """

    if module.OUTPUT_HTML_JINJA2:
        # Hier könnte man den Jinja2-Renderer einsetzen, um den Template-Code mit output_data zu rendern.
        return Template(module.OUTPUT_HTML_JINJA2)
    else:
        flat_data = module.flat_output(output_data)
        return generate_generic_table(flat_data)


def generate_generic_table(data: List[Dict[str, str]]) -> str:
    """
    Erzeugt eine einfache HTML-Tabelle aus einer Liste von Dictionaries.
    """

    if not data:
        return "<p>Keine Daten vorhanden.</p>"
    headers = data[0].keys()
    html = "<table class='table table-striped'>\n"
    html += "<thead><tr>" + "".join(f"<th>{header}</th>" for header in headers) + "</tr></thead>\n"
    html += "<tbody>\n"
    for row in data:
        html += "<tr>" + "".join(f"<td>{row.get(header, '')}</td>" for header in headers) + "</tr>\n"
    html += "</tbody>\n</table>"
    return html

def generate_csv_output(data: List[Dict[str, str]]) -> str:
    """
    Erzeugt einen CSV-Output aus einer Liste von Dictionaries.

    :param data: Liste von Dictionaries, wobei alle Dictionaries dieselben Keys besitzen.
    :return: CSV-String.
    """
    if not data:
        return "Keine Daten vorhanden."

    # Erstelle ein StringIO-Objekt als Puffer für den CSV-Output
    output = io.StringIO()
    # Bestimme die Header aus dem ersten Dictionary
    headers = list(data[0].keys())

    # Verwende csv.DictWriter, um den CSV-Output zu erzeugen
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=';')
    writer.writeheader()
    writer.writerows(data)

    # Hole den erzeugten CSV-String und schließe den Puffer
    csv_content = output.getvalue()
    output.close()
    return csv_content

def generate_xlsx_output(data: List[Dict[str, str]]) -> bytes:
    """
    Erzeugt einen XLSX-Output aus einer Liste von Dictionaries und gibt diesen als Bytes zurück.

    :param data: Liste von Dictionaries, wobei alle Dictionaries dieselben Keys besitzen.
    :return: XLSX-Dateiinhalt als Bytes.
    """


    wb = Workbook()
    ws = wb.active

    if not data:
        ws.append(["Keine Daten vorhanden."])
    else:
        headers = list(data[0].keys())
        ws.append(headers)
        for row in data:
            ws.append([row.get(header, "") for header in headers])

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream.read()


@app.get("/{toolgroup}/{tool}/raw/yaml")
def raw_yaml_endpoint(toolgroup: str, tool: str, request: Request):
    toolgroup_config = web_config.get('groups', {}).get(toolgroup, None)
    if not toolgroup_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Toolgroup '{toolgroup}' not found.",
            "web_config": web_config
        }, status_code=404)
    tool_config = toolgroup_config.get('tools', {}).get(tool, None)
    if not tool_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Tool '{tool}' not found in toolgroup '{toolgroup}'.",
            "web_config": web_config
        }, status_code=404)
    toolbox_module = tb.load_module(tool_config.get('module'))
    get_params = dict(request.query_params)
    output_data = toolbox_wrapper(toolbox_module, **get_params)
    yaml_output = yaml.safe_dump(output_data, default_flow_style=False)
    return Response(content=yaml_output, media_type="text/yaml")

@app.get("/{toolgroup}/{tool}/raw/json")
def raw_json_endpoint(toolgroup: str, tool: str, request: Request):
    toolgroup_config = web_config.get('groups', {}).get(toolgroup, None)
    if not toolgroup_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Toolgroup '{toolgroup}' not found.",
            "web_config": web_config
        }, status_code=404)
    tool_config = toolgroup_config.get('tools', {}).get(tool, None)
    if not tool_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Tool '{tool}' not found in toolgroup '{toolgroup}'.",
            "web_config": web_config
        }, status_code=404)
    toolbox_module = tb.load_module(tool_config.get('module'))
    get_params = dict(request.query_params)
    output_data = toolbox_wrapper(toolbox_module, **get_params)
    return JSONResponse(content=output_data)

@app.get("/{toolgroup}/{tool}/csv")
def csv_endpoint(toolgroup: str, tool: str, request: Request):
    toolgroup_config = web_config.get('groups', {}).get(toolgroup, None)
    if not toolgroup_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Toolgroup '{toolgroup}' not found.",
            "web_config": web_config
        }, status_code=404)
    tool_config = toolgroup_config.get('tools', {}).get(tool, None)
    if not tool_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Tool '{tool}' not found in toolgroup '{toolgroup}'.",
            "web_config": web_config
        }, status_code=404)
    toolbox_module = tb.load_module(tool_config.get('module'))
    get_params = dict(request.query_params)
    output_data = toolbox_wrapper(toolbox_module, **get_params)
    flat_data = toolbox_module.flat_output(output_data)
    csv_content = generate_csv_output(flat_data)
    filename = tool_config.get('module') + '.csv'
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content=csv_content, headers=headers, media_type="text/csv")

@app.get("/{toolgroup}/{tool}/xlsx")
def xlsx_endpoint(toolgroup: str, tool: str, request: Request):
    toolgroup_config = web_config.get('groups', {}).get(toolgroup, None)
    if not toolgroup_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Toolgroup '{toolgroup}' not found.",
            "web_config": web_config
        }, status_code=404)
    tool_config = toolgroup_config.get('tools', {}).get(tool, None)
    if not tool_config:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"Tool '{tool}' not found in toolgroup '{toolgroup}'.",
            "web_config": web_config
        }, status_code=404)
    toolbox_module = tb.load_module(tool_config.get('module'))
    get_params = dict(request.query_params)
    output_data = toolbox_wrapper(toolbox_module, **get_params)
    flat_data = toolbox_module.flat_output(output_data)
    xlsx_content = generate_xlsx_output(flat_data)
    filename = tool_config.get('module') + '.xlsx'
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content=xlsx_content, headers=headers, media_type="text/xlsx")




if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
