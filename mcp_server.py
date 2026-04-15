import httpx
import os
import urllib.parse

from mcp.server.fastmcp import FastMCP

# Initialize the FastMCP server
mcp = FastMCP("BudgetAppServer", host="0.0.0.0", port=8080)

# URL to your Django API
DJANGO_API_URL = os.environ.get("DJANGO_API_URL", "http://127.0.0.1:8000/api")

# Include authentication if you set it up in Django
HEADERS = {} 
# HEADERS = {"Authorization": "Token YOUR_SECRET_API_TOKEN"} 

@mcp.tool()
async def get_project_details(oracle_id: int) -> str:
    """Fetch the core details (name, budget, used hours) for a specific project by ID."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DJANGO_API_URL}/projects/{oracle_id}/", 
            headers=HEADERS
        )
        if response.status_code == 200:
            data = response.json()
            # If you used Method 2 (adding the field to the ProjectSerializer), 
            # you can include it right here:
            calc_hours = data.get('calculated_total_hours', 'Not calculated')
            return f"Project: {data['name']}, Budget: {data['calculated_total_hours']}h, Logged via Timecards: {calc_hours}h"
        return f"Error fetching project: {response.status_code}"

@mcp.tool()
async def get_project_timecards(project_id: int) -> str:
    """Fetch a list of all timecard items logged against a specific project ID."""
    async with httpx.AsyncClient() as client:
        # We use the filter functionality we added to the ViewSet via the query parameter
        response = await client.get(
            f"{DJANGO_API_URL}/timecards/?project={project_id}", 
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # DRF might paginate the results (wrap them in a 'results' key). 
            # We handle both paginated and unpaginated responses here.
            items = data.get('results', data) if isinstance(data, dict) else data
            
            if not items:
                return f"No timecards found for project ID {project_id}."
            
            # Format the output nicely for the AI to read
            formatted_timecards = []
            for item in items:
                formatted_timecards.append(
                    f"- {item['timecard_id']}: {item['total_hours']}h by {item['name']} "
                    f"on {item['start_date']} (Milestone: {item['milestone']}, Team: {item['team']})"
                )
            return "\n".join(formatted_timecards)
            
        return f"Error fetching timecards: {response.status_code}"

@mcp.tool()
async def get_project_total_hours(project_id: int) -> str:
    """Fetch the dynamically calculated sum of all timecard hours for a specific project ID."""
    # NOTE: Use this tool if you implemented Method 1 (the custom @action in views.py).
    # If you used Method 2 (added it to the Serializer), this tool is unnecessary!
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DJANGO_API_URL}/projects/{project_id}/total_hours/", 
            headers=HEADERS
        )
        if response.status_code == 200:
            data = response.json()
            return f"The total summed timecard hours for {data['project_name']} is {data['total_timecard_hours']}h."
        return f"Error fetching total hours: {response.status_code}"

@mcp.tool()
async def list_project_groups() -> str:
    """Fetch a list of all project groups, including the total summed hours for each group."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DJANGO_API_URL}/project-groups/", 
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle both paginated and unpaginated DRF responses
            items = data.get('results', data) if isinstance(data, dict) else data
            
            if not items:
                return "No project groups found."
            
            # Format the list for Cursor AI
            formatted_groups = []
            for item in items:
                calc_hours = item.get('calculated_total_hours', 'Not calculated')
                formatted_groups.append(
                    f"- ID {item['id']}: {item['name']} | Total Logged: {calc_hours}h"
                )
            return "\n".join(formatted_groups)
            
        return f"Error fetching project groups: {response.status_code}"

@mcp.tool()
async def get_project_group_details(group_id: int) -> str:
    """Fetch the specific details and total calculated hours for a single project group by its ID."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DJANGO_API_URL}/project-groups/{group_id}/", 
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            calc_hours = data.get('calculated_total_hours', 'Not calculated')
            
            return f"Project Group: {data['name']} (ID: {data['id']})\nTotal Hours Across All Projects: {calc_hours}h"
            
        return f"Error fetching project group: {response.status_code}"

@mcp.tool()
async def get_project_group_timecards(group_id: int, start_date: str = None, end_date: str = None) -> str:
    """
    Fetch a list of timecards for a specific project group ID. 
    Optionally provide a start_date and/or end_date in 'YYYY-MM-DD' format to filter the results.
    """
    # Build the query parameters dynamically based on what the AI provides
    query_params = {}
    if start_date:
        query_params['start_date'] = start_date
    if end_date:
        query_params['end_date'] = end_date
        
    # Convert the dictionary to a URL query string (e.g., "?start_date=2026-04-01")
    query_string = f"?{urllib.parse.urlencode(query_params)}" if query_params else ""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DJANGO_API_URL}/project-groups/{group_id}/timecards/{query_string}", 
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if not data:
                return f"No timecards found for project group {group_id} in that date range."
            
            # Format the output nicely for Cursor to read
            formatted_timecards = []
            for item in data:
                formatted_timecards.append(
                    f"- {item['timecard_id']}: {item['total_hours']}h by {item['name']} "
                    f"on {item['start_date']} (Project: {item['project']})"
                )
            return "\n".join(formatted_timecards)
            
        return f"Error fetching group timecards: {response.status_code} - {response.text}"

@mcp.tool()
async def upload_timecards_via_csv(csv_text_content: str) -> str:
    """
    Use this tool to upload new timecards to the database via CSV.
    Read the local CSV file from the workspace, and pass its raw text content into this tool's 'csv_text_content' parameter.
    """
    
    # We create a dictionary formatted for httpx's multipart/form-data upload.
    # We name the virtual file "timecards.csv" and encode the raw text back to bytes.
    files = {
        'file': ('timecards.csv', csv_text_content.encode('utf-8'), 'text/csv')
    }
    
    # NOTE: When sending files, we DO NOT send standard headers like 'Content-Type: application/json'.
    # httpx will automatically generate the correct multipart boundary headers.
    # If you have an Authorization header, you must keep it, but strip out Content-Type if you defined it globally.
    upload_headers = {k: v for k, v in HEADERS.items() if k.lower() != 'content-type'}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DJANGO_API_URL}/timecards/upload_csv/", 
            files=files,
            headers=upload_headers
        )
        
        if response.status_code == 200:
            return f"Success: {response.json().get('status', 'Imported')}"
        
        return f"Error uploading CSV: {response.status_code} - {response.text}"

if __name__ == "__main__":
    # Change transport from stdio to SSE, and bind to 0.0.0.0 for Docker
    mcp.run(transport="sse")