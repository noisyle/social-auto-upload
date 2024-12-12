from nicegui import ui, events, native
import os
from datetime import datetime
from conf import BASE_DIR
from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
from uploader.ks_uploader.main import ks_setup, KSVideo
from uploader.tencent_uploader.main import weixin_setup, TencentVideo
from uploader.tk_uploader.main_chrome import tiktok_setup, TiktokVideo
from utils.base_social_media import SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_KUAISHOU, SOCIAL_MEDIA_TIKTOK
from utils.constant import TencentZoneTypes
from utils.files_times import get_title_and_hashtags

COOKIES_DIR = os.path.join(BASE_DIR, 'cookies')
VIDEOS_DIR = os.path.join(BASE_DIR, 'videos')

@ui.page('/')
def render_root_page():
    render_frame()
    ui.label('首页')

@ui.page('/video')
def render_video_page():
    '''
    视频管理页面
    '''
    render_frame()

    def upload_video(e: events.UploadEventArguments):
        with open(os.path.join(VIDEOS_DIR, project_name.value+'.mp4'), 'wb') as f:
            f.write(e.content.read())
        ui.notify(f'添加视频 {project_name.value}.mp4', type='positive')

    def upload_cover(e: events.UploadEventArguments):
        with open(os.path.join(VIDEOS_DIR, project_name.value+'.png'), 'wb') as f:
            f.write(e.content.read())
        ui.notify(f'添加封面 {project_name.value}.png', type='positive')

    def submit():
        with open(os.path.join(VIDEOS_DIR, project_name.value+'.txt'), 'w', encoding='utf-8') as f:
            f.write(text.value)
        ui.notify(f'添加文案 {project_name.value}.txt', type='positive')
        dialog.close()
        grid.options['rowData'] = get_videos()
        grid.update()

    async def delete():
        row = await grid.get_selected_row()
        if not row:
            ui.notify('请选择要删除的视频', type='warning')
            return
        os.remove(os.path.join(VIDEOS_DIR, row['video']))
        os.remove(os.path.join(VIDEOS_DIR, row['text']))
        os.remove(os.path.join(VIDEOS_DIR, row['cover']))
        ui.notify(f'删除视频 {row["video"]}', type='positive')
        grid.options['rowData'] = get_videos()
        grid.update()

    async def show_publish_dialog():
        row = await grid.get_selected_row()
        if not row:
            ui.notify('请选择要发布的视频', type='warning')
            return
        publish_dialog.open()

    async def publish():
        if not account.value:
            ui.notify('请选择账号', type='warning')
            return
        platform = account.value.split('_', 1)[0]
        row = await grid.get_selected_row()
        video_file = os.path.join(VIDEOS_DIR, row['video'])
        account_file = os.path.join(COOKIES_DIR, account.value+'.json')
        title, tags = get_title_and_hashtags(os.path.join(VIDEOS_DIR, row['video']))
        if pt.value == 0:
            publish_date = 0
        else:
            if not date.value or not time.value:
                ui.notify('请选择发布日期和时间', type='warning')
                return
            publish_date = datetime.strptime(date.value + ' ' + time.value, '%Y-%m-%d %H:%M')
        ui.notify(f'正在调起发布页面', type='info')
        if platform == SOCIAL_MEDIA_DOUYIN:
            await douyin_setup(account_file, handle=False)
            app = DouYinVideo(title, video_file, tags, publish_date, account_file)
        elif platform == SOCIAL_MEDIA_KUAISHOU:
            await ks_setup(account_file, handle=True)
            app = KSVideo(title, video_file, tags, publish_date, account_file)
        elif platform == SOCIAL_MEDIA_TENCENT:
            await weixin_setup(account_file, handle=True)
            category = TencentZoneTypes.LIFESTYLE.value  # 标记原创需要否则不需要传
            app = TencentVideo(title, video_file, tags, publish_date, account_file, category)
        elif platform == SOCIAL_MEDIA_TIKTOK:
            await tiktok_setup(account_file, handle=True)
            app = TiktokVideo(title, video_file, tags, publish_date, account_file)
        await app.main()
        ui.notify(f'发布视频 {row["video"]} 到 {account.value}', type='positive')
        publish_dialog.close()

    # 上传视频对话框
    with ui.dialog() as dialog, ui.card().classes('min-w-96'):
        ui.label('上传视频')
        with ui.tabs().classes('w-full') as tabs:
            step1 = ui.tab('名称')
            step2 = ui.tab('上传视频')
            step3 = ui.tab('上传封面')
            step4 = ui.tab('编写文案')
        with ui.tab_panels(tabs, value=step1).classes('w-full') as panel:
            with ui.tab_panel(step1):
                project_name = ui.input(label='投稿名称', placeholder='输入投稿名称').classes('w-full')
                with ui.row().classes('w-full justify-end'):
                    ui.button('下一步', on_click=lambda e: panel.set_value(step2))
            with ui.tab_panel(step2):
                ui.upload(label='视频', on_upload=lambda e: upload_video(e), auto_upload=True) \
                    .props('accept=.mp4').classes('max-w-full')
                with ui.row().classes('w-full justify-end'):
                    ui.button('上一步', on_click=lambda e: panel.set_value(step1), color='white')
                    ui.button('下一步', on_click=lambda e: panel.set_value(step3))
            with ui.tab_panel(step3):
                ui.upload(label='封面', on_upload=lambda e: upload_cover(e), auto_upload=True) \
                    .props('accept=.png').classes('max-w-full')
                with ui.row().classes('w-full justify-end'):
                    ui.button('上一步', on_click=lambda e: panel.set_value(step2), color='white')
                    ui.button('下一步', on_click=lambda e: panel.set_value(step4))
            with ui.tab_panel(step4):
                text = ui.textarea(label='文案', placeholder='输入文案').classes('w-full')
                ui.label('第一行标题，第二行话题。话题以#开头，空格分隔。')
                with ui.row().classes('w-full justify-end'):
                    ui.button('取消', on_click=dialog.close, color='white')
                    ui.button('确定', on_click=lambda e: submit())

    # 发布视频对话框
    with ui.dialog() as publish_dialog, ui.card().classes('min-w-96'):
        ui.label('发布视频')
        accounts = get_accounts()
        account = ui.select([_['platform']+'_'+_['account'] for _ in accounts], label='选择账号').classes('w-full')
        pt = ui.radio({0: '立即发送', 1: '定时发送'}, value=0).props('inline')
        with ui.input('日期').bind_visibility(pt, 'value').classes('w-full') as date:
            with ui.menu().props('no-parent-event') as menu:
                with ui.date().bind_value(date):
                    with ui.row().classes('justify-end'):
                        ui.button('关闭', on_click=menu.close).props('flat')
            with date.add_slot('append'):
                ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')
        with ui.input('时间').bind_visibility(pt, 'value').classes('w-full') as time:
            with ui.menu().props('no-parent-event') as menu:
                with ui.time().bind_value(time):
                    with ui.row().classes('justify-end'):
                        ui.button('关闭', on_click=menu.close).props('flat')
            with time.add_slot('append'):
                ui.icon('access_time').on('click', menu.open).classes('cursor-pointer')

        with ui.row().classes('w-full justify-end'):
            ui.button('取消', on_click=publish_dialog.close, color='white')
            ui.button('确认发布', on_click=lambda: publish())

    with ui.row():
        ui.button('添加视频', on_click=dialog.open)
        ui.button('删除视频', color='amber', on_click=delete)
        ui.button('发布视频', color='green', on_click=show_publish_dialog)
    grid = ui.aggrid({'columnDefs': [
            {'headerName': '视频', 'field': 'video'},
            {'headerName': '文案', 'field': 'text'},
            {'headerName': '封面', 'field': 'cover'},
        ], 'rowData': get_videos(), 'rowSelection': 'single'})

@ui.page('/account')
def render_account_page():
    '''
    账号管理页面
    '''
    render_frame()

    async def show_auth_page():
        os.makedirs(COOKIES_DIR, exist_ok=True)
        account_file = os.path.join(COOKIES_DIR, f'{platform.value}_{account.value}.json')
        ui.notify(f'正在调起扫码页面', type='info')
        if platform.value == SOCIAL_MEDIA_DOUYIN:
            await douyin_setup(account_file, handle=True)
        elif platform.value == SOCIAL_MEDIA_KUAISHOU:
            await ks_setup(account_file, handle=True)
        elif platform.value == SOCIAL_MEDIA_TENCENT:
            await weixin_setup(account_file, handle=True)
        elif platform.value == SOCIAL_MEDIA_TIKTOK:
            await tiktok_setup(account_file, handle=True)
        dialog.close()
        grid.options['rowData'] = get_accounts()
        grid.update()

    async def delete():
        row = await grid.get_selected_row()
        if not row:
            ui.notify('请选择要删除的账号', type='warning')
            return
        os.remove(os.path.join(COOKIES_DIR, row["platform"]+'_'+row["account"]+'.json'))
        ui.notify(f'删除账号 {row["platform"]}_{row["account"]}', type='positive')
        grid.options['rowData'] = get_accounts()
        grid.update()

    with ui.dialog() as dialog, ui.card().classes('min-w-96'):
        ui.label('添加账号')
        platform = ui.select({
            SOCIAL_MEDIA_DOUYIN: '抖音',
            SOCIAL_MEDIA_KUAISHOU: '快手',
            SOCIAL_MEDIA_TENCENT: '视频号'
        }, value='douyin', label='选择短视频平台').classes('w-full')
        account = ui.input(label='账号别名').classes('w-full')
        with ui.row().classes('w-full justify-end'):
            ui.button('取消', on_click=dialog.close, color='white')
            ui.button('扫码授权', on_click=lambda: show_auth_page())

    with ui.row():
        ui.button('添加账号', on_click=dialog.open)
        ui.button('删除账号', color='amber', on_click=delete)
    grid = ui.aggrid({'columnDefs': [
            {'headerName': '短视频平台', 'field': 'platform'},
            {'headerName': '账号', 'field': 'account'},
        ], 'rowData': get_accounts(), 'rowSelection': 'single'})

@ui.page('/about')
def render_about_page():
    render_frame(False)
    ui.label('关于')

def get_videos():
    '''
    列出videos目录下的mp4文件
    '''
    videos = [file for file in os.listdir(VIDEOS_DIR) if file.endswith('.mp4')]
    return [{'video': _, 'text': _.rsplit('.', 1)[0] + '.txt', 'cover': _.rsplit('.', 1)[0] + '.png'} for _ in videos]

def get_accounts():
    '''
    列出cookies目录下的json文件
    '''
    accounts = [file.rsplit('.', 1)[0].split('_', 1) for file in os.listdir('cookies') if file.endswith('.json')]
    return [{'platform': _[0], 'account': _[1]} for _ in accounts]

def render_frame(show_menu: bool = True):
    '''
    统一绘制顶部导航栏和左侧菜单栏
    '''
    ui.page_title('Social Auto Upload')
    with ui.header():
        ui.button(icon='menu', on_click=lambda: left_drawer.toggle()).props('flat color=white')
        with ui.link(target = '/'):
            ui.button('social-auto-upload').props('flat').classes('text-blue-grey-1')
        with ui.link(target = '/about'):
            ui.button('About').props('flat').classes('text-blue-grey-1')

    with ui.left_drawer(value = show_menu).classes('bg-blue-grey-1') as left_drawer:
        with ui.link(target = '/video'):
            ui.button('视频管理').props('flat').classes('text-blue-grey-10')
        with ui.link(target = '/account'):
            ui.button('账号管理').props('flat').classes('text-blue-grey-10')

ui.run(reload=False, port=native.find_open_port())
