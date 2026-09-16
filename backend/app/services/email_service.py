import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from app.db.session import get_db_connection

logger = logging.getLogger(__name__)

def get_smtp_config() -> Optional[Dict[str, Any]]:
    """从数据库读取系统全局 SMTP 配置"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM system_settings WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return dict(row)
    except Exception as e:
        logger.error(f"读取 SMTP 配置失败: {e}")
        return None

def test_smtp_connection(host: str, port: int, user: str, password: str, to_email: str) -> Dict[str, Any]:
    """测试 SMTP 邮件连接并发送测试探测邮件"""
    if not host or not user or not password:
        return {"success": False, "message": "SMTP 服务器地址、用户名或密码不可为空"}
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "【MaintainWise 2.0】工业邮件服务通信测试成功"
    msg["From"] = user
    msg["To"] = to_email or user
    
    text_content = "MaintainWise 2.0 智能工厂系统已成功与您的工业企业邮件网关建立安全连接！"
    html_content = """
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h3 style="color: #0284c7;">🎉 MaintainWise 2.0 工业邮件通知网关连接成功</h3>
        <p>尊敬的工程师 / 管理员：</p>
        <p>您的工厂邮件服务器 (SMTP) 参数已正确配置并联通。未来设备突发报警、工单指派、维保超期告警将通过此信箱自动直达现场责任人！</p>
        <hr style="border: 0; border-top: 1px solid #cbd5e1; margin: 20px 0;" />
        <p style="font-size: 12px; color: #64748b;">MaintainWise 2.0 智能工厂设备管理系统 - 自动化监控服务</p>
    </div>
    """
    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            try:
                server.starttls()
            except Exception:
                pass
                
        server.login(user, password)
        server.sendmail(user, [to_email or user], msg.as_string())
        server.quit()
        return {"success": True, "message": f"测试邮件已成功发送至 {to_email or user}！"}
    except Exception as e:
        logger.warning(f"SMTP 测试连接失败: {e}")
        return {"success": False, "message": f"SMTP 验证失败: {str(e)}"}

def send_notification_email_sync(to_email: str, subject: str, content: str, html: Optional[str] = None) -> bool:
    """同步发送邮件，若配置未启用则直接安全跳过"""
    if not to_email:
        return False
        
    cfg = get_smtp_config()
    if not cfg or not cfg.get("smtp_enabled"):
        return False
        
    host = cfg.get("smtp_host")
    port = int(cfg.get("smtp_port") or 465)
    user = cfg.get("smtp_user")
    password = cfg.get("smtp_pass")
    
    if not host or not user or not password:
        return False
        
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_email
        
        msg.attach(MIMEText(content, "plain", "utf-8"))
        if html:
            msg.attach(MIMEText(html, "html", "utf-8"))
            
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            try:
                server.starttls()
            except Exception:
                pass
                
        server.login(user, password)
        server.sendmail(user, [to_email], msg.as_string())
        server.quit()
        logger.info(f"成功向 {to_email} 发送邮件: {subject}")
        return True
    except Exception as e:
        logger.error(f"发送邮件异常 ({to_email}): {e}")
        return False

def send_email_in_background(to_email: str, subject: str, content: str, html: Optional[str] = None):
    """异步后台线程分发邮件，绝对不阻塞 API 主线程"""
    if not to_email:
        return
    t = threading.Thread(target=send_notification_email_sync, args=(to_email, subject, content, html), daemon=True)
    t.start()

def notify_work_order_assigned(assignee_email: str, assignee_name: str, order_no: str, equipment_name: str, title: str, urgency: str):
    """工单指派通知邮件"""
    subject = f"【工单指派通知】{order_no} 现场维修任务已指派给您"
    content = f"尊敬的 {assignee_name}：\n设备【{equipment_name}】发生故障：{title}（紧急度：{urgency}），工单号：{order_no}。请尽快前往车间现场排查！"
    html = f"""
    <div style="font-family: sans-serif; padding: 16px; border: 1px solid #cbd5e1; border-radius: 8px;">
        <h3 style="color: #ef4444; margin-top: 0;">⚡ 现场维修工单指派提醒</h3>
        <p><strong>责任技术员：</strong>{assignee_name}</p>
        <p><strong>工单编号：</strong><code>{order_no}</code></p>
        <p><strong>故障设备：</strong><span style="color: #0284c7; font-weight: bold;">{equipment_name}</span></p>
        <p><strong>故障简述：</strong>{title}</p>
        <p><strong>紧急程度：</strong><span style="color: #dc2626; font-weight: bold;">{urgency}</span></p>
        <hr style="border: 0; border-top: 1px dashed #cbd5e1;" />
        <p style="font-size: 13px; color: #64748b;">请技术员携带安全防护用具前往现场排故抢修，并在完成后填报真实根本原因与解决步骤。</p>
    </div>
    """
    send_email_in_background(assignee_email, subject, content, html)

def notify_maintenance_anomaly(engineer_email: str, engineer_name: str, equipment_name: str, anomaly_desc: str, record_no: str):
    """设备巡检发现异常通知负责工程师"""
    subject = f"【维保异常隐患预警】{equipment_name} 巡检发现异常"
    content = f"尊敬的工程师 {engineer_name}：\n设备【{equipment_name}】在现场巡检打卡中发现异常隐患：{anomaly_desc}，打卡记录号：{record_no}。系统已联锁生成抢修工单，请及时跟进核查！"
    html = f"""
    <div style="font-family: sans-serif; padding: 16px; border: 1px solid #fecaca; background-color: #fff5f5; border-radius: 8px;">
        <h3 style="color: #b91c1c; margin-top: 0;">🚨 设备维保巡检异常隐患报告</h3>
        <p><strong>负责工程师：</strong>{engineer_name}</p>
        <p><strong>故障设备：</strong><strong>{equipment_name}</strong></p>
        <p><strong>维保单号：</strong><code>{record_no}</code></p>
        <p><strong>隐患详述：</strong><span style="color: #991b1b;">{anomaly_desc}</span></p>
        <hr style="border: 0; border-top: 1px dashed #fca5a5;" />
        <p style="font-size: 13px; color: #7f1d1d;">系统已自动联锁跃迁设备状态为检修中，并生成联动突发维修工单，请工程师到场复查试车！</p>
    </div>
    """
    send_email_in_background(engineer_email, subject, content, html)

def notify_password_expired(user_email: str, username: str, full_name: str):
    """密码超期冻结通知邮件"""
    subject = "【账号安全冻结通知】MaintainWise 系统登录密码超期已冻结"
    content = f"尊敬的 {full_name}：\n您的 MaintainWise 账号（{username}）登录密码已超过 180 天未修改。为符合工业安全合规，账号已被临时冻结。请联系车间系统管理员解冻并重置密码。"
    html = f"""
    <div style="font-family: sans-serif; padding: 16px; border: 1px solid #f87171; border-radius: 8px;">
        <h3 style="color: #dc2626;">🔒 登录密码超期账户冻结提醒</h3>
        <p>尊敬的 <strong>{full_name} ({username})</strong>：</p>
        <p>根据工业数据安全规范，系统密码每 180 天需强制更新。您的密码已超期，当前账号已被安全冻结保护。</p>
        <p>请及时联系车间主管工程师或系统管理员解冻并更新密码。</p>
    </div>
    """
    send_email_in_background(user_email, subject, content, html)

def notify_password_expiring_soon(user_email: str, username: str, full_name: str, days_remaining: int):
    """密码即将到期预警邮件"""
    subject = f"【密码临期提醒】您的登录密码将在 {days_remaining} 天后到期"
    content = f"尊敬的 {full_name}：\n您的账号（{username}）密码将在 {days_remaining} 天后到达 180 天安全期限。请及时登录系统并在个人设置中更新密码，避免到期自动冻结影响生产排程。"
    html = f"""
    <div style="font-family: sans-serif; padding: 16px; border: 1px solid #fbbf24; border-radius: 8px;">
        <h3 style="color: #d97706;">⏰ 登录密码临期修改提醒</h3>
        <p>尊敬的 <strong>{full_name} ({username})</strong>：</p>
        <p>您的密码将在 <strong>{days_remaining}</strong> 天后达到 180 天使用上限。</p>
        <p>为保障作业顺畅，请及时在右上角点击个人信息修改密码。</p>
    </div>
    """
    send_email_in_background(user_email, subject, content, html)

def notify_maintenance_due(engineer_email: str, engineer_name: str, equipment_name: str, running_mode: str, remaining_hours: float, interval_hours: float, est_days: Optional[float]):
    """设备维保倒计时临期/超期邮件预警"""
    mode_cn = "间歇作业型 (按开机时长累计)" if running_mode == "INTERMITTENT" else "连续运行型 (24h常开)"
    is_overdue = remaining_hours <= 0
    if is_overdue:
        subject = f"【🚨 设备超期维保告警】{equipment_name} 已超出维护工时周期！"
        status_text = f"已超出设定周期 {abs(remaining_hours)} 小时"
        color = "#dc2626"
    else:
        subject = f"【⏰ 设备维保临期预警】{equipment_name} 距离维护周期还剩 {remaining_hours} 小时"
        est_tip = f"，按近期开机习惯预计将在 {est_days} 天后到达阈值" if est_days is not None else ""
        status_text = f"剩余开机工时 {remaining_hours} 小时{est_tip}"
        color = "#d97706"

    content = f"尊敬的工程师 {engineer_name}：\n设备【{equipment_name}】({mode_cn}) 维护周期为 {interval_hours} 小时。当前状态：{status_text}。请提前备料并合理协调车间停机维护窗口！"
    html = f"""
    <div style="font-family: sans-serif; padding: 16px; border: 1px solid {color}; border-radius: 8px;">
        <h3 style="color: {color}; margin-top: 0;">{"🚨 设备超期维保告警" if is_overdue else "⏰ 设备维保工时临期预警"}</h3>
        <p><strong>负责工程师：</strong>{engineer_name}</p>
        <p><strong>设备名称：</strong><strong>{equipment_name}</strong></p>
        <p><strong>运行模式：</strong><span style="color: #475569;">{mode_cn}</span></p>
        <p><strong>设定维护周期：</strong>{interval_hours} 小时</p>
        <p><strong>当前预警状态：</strong><strong style="color: {color};">{status_text}</strong></p>
        <hr style="border: 0; border-top: 1px dashed #cbd5e1;" />
        <p style="font-size: 13px; color: #64748b;">请工程师提前在仓库备齐专用润滑脂、备品耗材，并在系统【设备维护】模块安排执行维护打卡。</p>
    </div>
    """
    send_email_in_background(engineer_email, subject, content, html)

