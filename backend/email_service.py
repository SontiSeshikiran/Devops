import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_reset_email(to_email: str, reset_link: str):
    return send_reset_password_email(to_email=to_email, reset_link=reset_link)

def send_welcome_email(to_email: str, reset_link: str, password: str = None):
    api_key = os.getenv("UNOSEND_API_KEY")
    
    if not api_key:
        print("====== MOCK EMAIL (No UNOSEND_API_KEY found) ======")
        print(f"To: {to_email}")
        print(f"Password: {password}")
        print(f"Link: {reset_link}")
        print("==================================================")
        return True

    url = "https://api.unosend.co/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    from_email = os.getenv("UNOSEND_FROM_EMAIL", "identity@blutor.io")
    
    credentials_block = ""
    if password:
        credentials_block = f"""
        <tr>
          <td style="padding-bottom: 32px;">
            <div style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 12px; padding: 24px;">
              <p style="color: #818cf8; font-size: 14px; font-weight: 600; margin: 0 0 16px 0; text-transform: uppercase; letter-spacing: 0.05em;">Initial Access Credentials</p>
              <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="padding-bottom: 8px;">
                    <span style="color: #94a3b8; font-size: 12px; display: block; margin-bottom: 4px;">Operator Identity</span>
                    <code style="color: #f1f5f9; font-size: 16px; font-family: monospace;">{to_email}</code>
                  </td>
                </tr>
                <tr>
                  <td>
                    <span style="color: #94a3b8; font-size: 12px; display: block; margin-bottom: 4px;">Temporary Access Key</span>
                    <code style="color: #f1f5f9; font-size: 16px; font-family: monospace;">{password}</code>
                  </td>
                </tr>
              </table>
            </div>
          </td>
        </tr>
        """

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Outfit:wght@600&display=swap" rel="stylesheet">
    </head>
    <body style="margin: 0; padding: 0; background-color: #020617; font-family: 'Inter', system-ui, -apple-system, sans-serif;">
      <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #020617; padding: 40px 20px;">
        <tr>
          <td align="center">
            <table width="100%" max-width="600" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; background: #0f172a; border: 1px solid #1e293b; border-radius: 20px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
              <!-- Header Gradient Bar -->
              <tr>
                <td height="4" style="background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%);"></td>
              </tr>
              <!-- Content -->
              <tr>
                <td style="padding: 48px 40px;">
                  <table width="100%" border="0" cellspacing="0" cellpadding="0">
                    <tr>
                      <td style="padding-bottom: 24px;">
                        <span style="color: #6366f1; font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.1em;">Identity Provisioned</span>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding-bottom: 20px;">
                        <h1 style="color: #f8fafc; font-family: 'Outfit', sans-serif; font-size: 32px; font-weight: 600; margin: 0; line-height: 1.2;">Welcome to your <br><span style="color: #818cf8;">BluTOR Command Center</span></h1>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding-bottom: 32px;">
                        <p style="color: #94a3b8; font-size: 16px; line-height: 1.6; margin: 0;">An administrator has provisioned your professional identity on the BluTOR Intelligence Platform. Your secure environment is ready for deployment.</p>
                      </td>
                    </tr>
                    {credentials_block}
                    <tr>
                      <td align="center" style="padding-bottom: 32px;">
                        <a href="{reset_link}" style="display: inline-block; padding: 16px 32px; background: #6366f1; color: #ffffff; text-decoration: none; border-radius: 12px; font-weight: 600; font-size: 16px; border: 1px solid #818cf8; box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3);">Initialize Secure Identity</a>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding: 24px; background: #1e293b; border-radius: 12px; border: 1px solid #334155;">
                        <p style="color: #f1f5f9; font-size: 14px; font-weight: 600; margin: 0 0 8px 0;">Next steps:</p>
                        <ul style="color: #94a3b8; font-size: 14px; margin: 0; padding-left: 20px; line-height: 1.5;">
                          <li>Access the link within 24 hours to set your password.</li>
                          <li>Configure Multi-Factor Authentication (MFA) on first login.</li>
                          <li>Review the mission briefing in the dashboard.</li>
                        </ul>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="padding: 32px 40px; background: #020617; border-top: 1px solid #1e293b; text-align: center;">
                  <p style="color: #64748b; font-size: 11px; margin: 0 0 16px 0; line-height: 1.5;">
                    &copy; 2026 Blue Cloud Softech. BluTOR Intelligence Platform.<br>
                    123 Security Plaza, Suite 500, San Jose, CA 95131
                  </p>
                  <p style="color: #475569; font-size: 11px; margin: 0; line-height: 1.5;">
                    This is a required security notification regarding your BluTOR operator identity.<br>
                    You are receiving this because an administrator provisioned your account.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    from_email = os.getenv("UNOSEND_FROM_EMAIL", "identity@blutor.io")
    friendly_from = f"BluTOR Security <{from_email}>"
    
    # ... (rest of the credentials block logic stays the same)
    
    # ...
    
    data = {
        "from": friendly_from,
        "to": [to_email],
        "subject": "BluTOR Action Required: Secure Your Identity",
        "html": html_body
    }

    try:
        # Note: Verify protocol (https) and endpoint path for Uno Send
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code in [200, 201, 202]:
            print(f"Welcome email successfully sent to {to_email}")
            print(f"Uno Send API Response: {response.text}")
            return True
        else:
            print(f"Failed to send email to {to_email}. Status code: {response.status_code}, Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending email to {to_email}: {e}")
        return False

def send_reset_password_email(to_email: str, reset_link: str):
    api_key = os.getenv("UNOSEND_API_KEY")
    
    if not api_key:
        print("====== MOCK RESET EMAIL (No UNOSEND_API_KEY found) ======")
        print(f"To: {to_email}")
        print(f"Link: {reset_link}")
        print("========================================================")
        return True

    url = "https://api.unosend.co/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    from_email = os.getenv("UNOSEND_FROM_EMAIL", "identity@blutor.io")
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Outfit:wght@600&display=swap" rel="stylesheet">
    </head>
    <body style="margin: 0; padding: 0; background-color: #020617; font-family: 'Inter', system-ui, -apple-system, sans-serif;">
      <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #020617; padding: 40px 20px;">
        <tr>
          <td align="center">
            <table width="100%" max-width="600" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; background: #0f172a; border: 1px solid #1e293b; border-radius: 20px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
              <!-- Header Gradient Bar -->
              <tr>
                <td height="4" style="background: linear-gradient(90deg, #f43f5e 0%, #6366f1 100%);"></td>
              </tr>
              <!-- Content -->
              <tr>
                <td style="padding: 48px 40px;">
                  <table width="100%" border="0" cellspacing="0" cellpadding="0">
                    <tr>
                      <td style="padding-bottom: 24px;">
                        <span style="color: #f43f5e; font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.1em;">Security Authorization</span>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding-bottom: 20px;">
                        <h1 style="color: #f8fafc; font-family: 'Outfit', sans-serif; font-size: 32px; font-weight: 600; margin: 0; line-height: 1.2;">Password Reset <br><span style="color: #fb7185;">Request</span></h1>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding-bottom: 32px;">
                        <p style="color: #94a3b8; font-size: 16px; line-height: 1.6; margin: 0;">We received a request to reset the password for your BluTOR account. For security, this link will expire in 24 hours.</p>
                      </td>
                    </tr>
                    <tr>
                      <td align="center" style="padding-bottom: 32px;">
                        <a href="{reset_link}" style="display: inline-block; padding: 16px 32px; background: #f43f5e; color: #ffffff; text-decoration: none; border-radius: 12px; font-weight: 600; font-size: 16px; border: 1px solid #fb7185; box-shadow: 0 10px 15px -3px rgba(244, 63, 94, 0.3);">Confirm Security Reset</a>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding: 20px; background: rgba(244, 63, 94, 0.1); border-radius: 12px; border: 1px solid rgba(244, 63, 94, 0.2);">
                        <p style="color: #fca5a5; font-size: 14px; margin: 0; line-height: 1.5;"><strong>Security Note:</strong> If you did not initiate this request, please contact your Security Operations Center (SOC) immediately.</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <!-- Footer -->
              <tr>
                <td style="padding: 32px 40px; background: #020617; border-top: 1px solid #1e293b; text-align: center;">
                  <p style="color: #64748b; font-size: 11px; margin: 0 0 16px 0; line-height: 1.5;">
                    &copy; 2026 Blue Cloud Softech. BluTOR Intelligence Platform.<br>
                    123 Security Plaza, Suite 500, San Jose, CA 95131
                  </p>
                  <p style="color: #475569; font-size: 11px; margin: 0; line-height: 1.5;">
                    This automated security notification was triggered by a password reset request.<br>
                    If you did not request this, please ignore this email or contact your SOC.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    from_email = os.getenv("UNOSEND_FROM_EMAIL", "identity@blutor.io")
    friendly_from = f"BluTOR Security <{from_email}>"

    data = {
        "from": friendly_from,
        "to": [to_email],
        "subject": "BluTOR Security: Password Reset Request",
        "html": html_body
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code in [200, 201, 202]:
            print(f"Reset email successfully sent to {to_email}")
            return True
        else:
            print(f"Failed to send reset email to {to_email}. Status code: {response.status_code}, Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending reset email: {e}")
        return False
