import pandas as pd
import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="ServiceBrain 工作台", page_icon="⚙️", layout="wide")

# ==========================
# 侧边栏导航
# ==========================
st.sidebar.title("电商售后智能RAG知识库平台")
menu = st.sidebar.radio("工作台", ["客户与订单中心", "智能售后问诊台", "知识库"])

# ==========================
# 页面一：企业级业务 CRUD 平台
# ==========================
if menu == "客户与订单中心":
    st.title("客户与订单中心")

    st.markdown("### 📈 实时数据")
    try:
        # 请求真实 KPI 接口
        kpi_res = requests.get(f"{API_URL}/admin/kpi")
        if kpi_res.status_code == 200:
            kpi_data = kpi_res.json()
            # 创建 4 列横向布局
            col1, col2, col3, col4 = st.columns(4)
            # 在每一列中放置一个原生 metric 组件
            with col1:
                st.metric(label="平台总客户数", value=kpi_data.get("total_customers", 0))
            with col2:
                st.metric(label="在保设备总数", value=kpi_data.get("total_assets", 0))
            with col3:
                st.metric(label="待人工处理工单", value=kpi_data.get("pending_orders", 0))
            with col4:
                st.metric(label="AI 自动解决率", value=kpi_data.get("ai_resolved_rate", "0%"))
        else:
            st.warning("无法获取实时指标，请检查后端 API 状态。")

    except Exception as e:
        st.error(f"连接后端失败: {e}")

    st.divider()

    # 🌟多标签页工作区
    tab1, tab2, tab3= st.tabs(["客户页面", "订单查询", "管理员页面"])

    # 🌟通用 Toast 拦截器：放在 Tab 外，负责显示刷新后的操作结果
    if "sync_msg" in st.session_state:
        if st.session_state["sync_status"] == "success":
            st.toast(st.session_state["sync_msg"], icon="✅")
        else:
            st.error(st.session_state["sync_msg"])
        del st.session_state["sync_msg"], st.session_state["sync_status"]

    with tab1:
        st.markdown("#### 快速录入通道")
        col_c, col_o = st.columns(2)
        with col_c:
            with st.form("customer_form", clear_on_submit=True):
                st.caption("1. 建立客户档案")
                c_name = st.text_input("客户姓名")
                c_phone = st.text_input("手机号 (11位数字)")
                if st.form_submit_button("注册客户"):
                    res = requests.post(f"{API_URL}/customers/", json={"name": c_name, "phone": c_phone})
                    if res.status_code == 201:
                        st.success("客户录入成功！")
                    else:
                        st.error(res.json().get("detail", "录入失败"))

        with col_o:
            with st.form("order_form", clear_on_submit=True):
                st.caption("2. 绑定购买的设备")
                o_phone = st.text_input("关联客户手机号")
                o_category = st.selectbox("商品品类", ["大家电", "3C数码", "智能家居"])
                o_model = st.text_input("精确型号 (如: 华为Mate60, 海尔XQG100)")
                o_date = st.date_input("购买日期")
                if st.form_submit_button("绑定资产"):
                    payload = {"phone": o_phone, "product_category": o_category, "product_model": o_model,
                               "purchase_date": str(o_date)}
                    res = requests.post(f"{API_URL}/orders/", json=payload)
                    if res.status_code == 201:
                        st.success("资产绑定成功！")
                    else:
                        st.error(res.json().get("detail", "绑定失败"))

    with tab2:
        # 数据检索与表格展示
        st.markdown("#### 订单查询")
        search_kw = st.text_input("🔍 输入手机号查询该客户名下所有资产：")
        if search_kw:
            res_info = requests.get(f"{API_URL}/orders/{search_kw}")
            if res_info.status_code == 200:
                data = res_info.json()
                st.write(
                    f"**客户姓名**: {data['customer']['name']} | **客户等级**: {data['customer']['customer_level']}")
                st.dataframe(data['assets'], use_container_width=True)
            else:
                st.warning("未查询到资产记录。")

    with tab3:

        st.info("💡 提示：双击单元格修改数据，或选中最左侧复选框按 Delete 删除行。点击『同步』保存。")

        # crud 工单表
        st.markdown("#### 🛠️ 售后工单管理")
        try:
            res_wo = requests.get(f"{API_URL}/admin/work-orders")
            if res_wo.status_code == 200:
                wo_data = res_wo.json()
                if wo_data:
                    df_wo = pd.DataFrame(wo_data)
                    # 容错处理：确保只展示存在的列
                    wo_cols = ['id', 'asset_id', 'issue_description', 'ai_diagnosis', 'status']
                    exist_wo_cols = [c for c in wo_cols if c in df_wo.columns]
                    df_wo_display = df_wo[exist_wo_cols]

                    # 渲染编辑器，禁用不可修改的列，仅允许修改 status
                    edited_wo_df = st.data_editor(
                        df_wo_display,
                        key="wo_editor",
                        num_rows="dynamic",
                        disabled=["id", "asset_id", "issue_description", "ai_diagnosis"],
                        use_container_width=True
                    )

                    wo_changes = st.session_state.get("wo_editor", {})

                    if st.button("💾 同步变更", type="primary", key="btn_sync_wo"):
                        wo_has_changes = False
                        wo_error_msgs = []

                        # 1. 提取修改 (Update)
                        if wo_changes.get("edited_rows"):
                            wo_has_changes = True
                            for row_index, updated_fields in wo_changes["edited_rows"].items():
                                row_idx = int(row_index)
                                real_id = str(df_wo_display.iloc[row_idx]['id'])  # 注意：工单ID是字符串

                                # 工单更新接口只接收 status 字段
                                payload = {
                                    "status": updated_fields.get("status", df_wo_display.iloc[row_idx]['status'])
                                }
                                requests.put(f"{API_URL}/admin/work-orders/{real_id}", json=payload)

                        # 2. 提取删除 (Delete)
                        if wo_changes.get("deleted_rows"):
                            wo_has_changes = True
                            for row_index in wo_changes["deleted_rows"]:
                                real_id = str(df_wo_display.iloc[row_index]['id'])
                                d_res = requests.delete(f"{API_URL}/admin/work-orders/{real_id}")
                                if d_res.status_code != 200:
                                    wo_error_msgs.append(d_res.json().get('detail', '未知删除错误'))

                        if wo_has_changes:
                            if len(wo_error_msgs) == 0:
                                st.session_state["sync_msg"] = "工单数据库同步成功！"
                                st.session_state["sync_status"] = "success"
                            else:
                                st.session_state["sync_msg"] = f"同步异常：{wo_error_msgs[0]}"
                                st.session_state["sync_status"] = "error"

                            del st.session_state["wo_editor"]
                            st.rerun()
                        else:
                            st.warning("没有检测到任何工单数据变更。")
                else:
                    st.info("当前没有工单数据。")
        except Exception as e:
            st.error(f"拉取工单数据失败: {e}")

        st.divider()

        # crud 客户表
        st.markdown("#### 👤 客户档案管理")

        try:
            res_cust = requests.get(f"{API_URL}/admin/customers")
            if res_cust.status_code == 200:
                cust_data = res_cust.json()
                if cust_data:
                    df_cust = pd.DataFrame(cust_data)
                    df_display = df_cust[['id', 'name', 'phone', 'customer_level', 'create_time']]

                    edited_df = st.data_editor(
                        df_display,
                        key="customer_editor",
                        num_rows="dynamic",
                        disabled=["id", "customer_level", "create_time"],
                        use_container_width=True
                    )

                    changes = st.session_state.get("customer_editor", {})

                    if st.button("💾 同步变更", type="primary", key="btn_sync_customer"):
                        has_changes = False
                        error_msgs = []  # 收集后端报错信息

                        # 1. 提取修改 (Update)
                        if changes.get("edited_rows"):
                            has_changes = True
                            for row_index, updated_fields in changes["edited_rows"].items():
                                row_idx = int(row_index)
                                real_id = int(df_display.iloc[row_idx]['id'])
                                payload = {
                                    "name": updated_fields.get("name", df_display.iloc[row_idx]['name']),
                                    "phone": updated_fields.get("phone", df_display.iloc[row_idx]['phone'])
                                }
                                requests.put(f"{API_URL}/admin/customers/{real_id}", json=payload)

                        # 2. 提取删除 (Delete)
                        if changes.get("deleted_rows"):
                            has_changes = True
                            for row_index in changes["deleted_rows"]:
                                real_id = int(df_display.iloc[row_index]['id'])
                                res = requests.delete(f"{API_URL}/admin/customers/{real_id}")
                                # 如果删除失败（触发外键保护），把后端发来的报错抓出来
                                if res.status_code != 200:
                                    error_msgs.append(res.json().get('detail', '未知删除错误'))

                        if has_changes:
                            # 3. 把执行结果存入 session_state，留给刷新后的页面显示
                            if len(error_msgs) == 0:
                                st.session_state["sync_msg"] = "客户数据库同步成功！"
                                st.session_state["sync_status"] = "success"
                            else:
                                st.session_state["sync_msg"] = f"同步异常：{error_msgs[0]}"
                                st.session_state["sync_status"] = "error"

                            # 4. 强制清空编辑器的缓存，这步非常关键
                            del st.session_state["customer_editor"]
                            st.rerun()  # 立即刷新页面
                        else:
                            st.warning("没有检测到任何客户数据变更。")
                else:
                    st.info("当前没有客户数据。")
        except Exception as e:
            st.error(f"拉取客户数据失败: {e}")

        st.divider()

        # crud 设备资产表
        st.markdown("#### 📦 客户订单管理")
        try:
            res_asset = requests.get(f"{API_URL}/admin/assets")
            if res_asset.status_code == 200:
                asset_data = res_asset.json()
                if asset_data:
                    df_asset = pd.DataFrame(asset_data)
                    # 容错处理：确保只展示存在的列
                    asset_cols = ['id', 'customer_id', 'product_category', 'product_model', 'warranty_status', 'purchase_date']
                    exist_cols = [c for c in asset_cols if c in df_asset.columns]
                    df_asset_display = df_asset[exist_cols]

                    edited_asset_df = st.data_editor(
                        df_asset_display,
                        key="asset_editor",
                        num_rows="dynamic",
                        disabled=["id", "customer_id", "warranty_status", "purchase_date"], # 禁止修改关键字段和时间
                        use_container_width=True
                    )

                    asset_changes = st.session_state.get("asset_editor", {})

                    if st.button("💾 同步变更", type="primary", key="btn_sync_asset"):
                        asset_has_changes = False
                        asset_error_msgs = []

                        # 1. 提取修改 (Update)
                        if asset_changes.get("edited_rows"):
                            asset_has_changes = True
                            for row_index, updated_fields in asset_changes["edited_rows"].items():
                                row_idx = int(row_index)
                                real_id = int(df_asset_display.iloc[row_idx]['id'])
                                payload = {
                                    "product_category": updated_fields.get("product_category", df_asset_display.iloc[row_idx]['product_category']),
                                    "product_model": updated_fields.get("product_model", df_asset_display.iloc[row_idx]['product_model'])
                                }
                                requests.put(f"{API_URL}/admin/assets/{real_id}", json=payload)

                        # 2. 提取删除 (Delete)
                        if asset_changes.get("deleted_rows"):
                            asset_has_changes = True
                            for row_index in asset_changes["deleted_rows"]:
                                real_id = int(df_asset_display.iloc[row_index]['id'])
                                d_res = requests.delete(f"{API_URL}/admin/assets/{real_id}")
                                if d_res.status_code != 200:
                                    asset_error_msgs.append(d_res.json().get('detail', '未知删除错误'))

                        if asset_has_changes:
                            if len(asset_error_msgs) == 0:
                                st.session_state["sync_msg"] = "设备资产数据库同步成功！"
                                st.session_state["sync_status"] = "success"
                            else:
                                st.session_state["sync_msg"] = f"同步异常：{asset_error_msgs[0]}"
                                st.session_state["sync_status"] = "error"

                            del st.session_state["asset_editor"]
                            st.rerun()
                        else:
                            st.warning("没有检测到任何设备资产数据变更。")
                else:
                    st.info("当前没有设备资产数据。")
        except Exception as e:
            st.error(f"拉取设备资产数据失败: {e}")

# ==========================
# 页面二：智能售后问诊台 (RAG)
# ==========================
elif menu == "智能售后问诊台":
    st.title("🤖 智能售后")
    st.markdown("系统会自动去数据库查设备，再结合知识库回答问题。")

    # 身份验证
    search_phone = st.text_input("请输入手机号：", placeholder="输入您的手机号")

    if search_phone:
        # 1. 优先展示从 MySQL 查到的结构化事实
        res_info = requests.get(f"{API_URL}/orders/{search_phone}")
        if res_info.status_code == 200:
            data = res_info.json()
            st.info(f"✅ 身份识别成功！客户：**{data['customer']['name']}**")
            st.write("名下绑定的设备资产如下：")
            st.dataframe(data['assets'], use_container_width=True)

            st.divider()

            # 2. RAG 对话框
            st.subheader("💬 描述您的问题")
            issue = st.text_area("故障描述：", placeholder="例如：空调开机后一直滴水，而且不制冷...")

            if st.button("🚀 呼叫智能售后", type="primary"):
                if not issue:
                    st.warning("请先输入故障描述！")
                else:
                    with st.spinner("正在提取后台参数并检索知识库，请稍候..."):
                        try:
                            # 携带手机号和问题去请求我们封装好的 RAG 路由
                            chat_res = requests.post(f"{API_URL}/chat/", json={"phone": search_phone, "issue": issue})
                            if chat_res.status_code == 200:
                                reply_data = chat_res.json()
                                st.success(f"诊断完成！已生成系统工单：**{reply_data['work_order_id']}**")
                                st.markdown("### 🤖 AI 回复:")
                                st.info(reply_data['ai_reply'])
                            else:
                                st.error(f"大模型服务异常: {chat_res.json().get('detail', '未知错误')}")
                        except Exception as e:
                            st.error(f"请求后端聊天接口失败: {e}")
        else:
            st.warning("查无此人，系统拒绝提供服务。请先去【客户与订单中心】注册并绑定资产。")

# ==========================
# 页面三：RAG 知识库管理后台
# ==========================
elif menu == "知识库":
    st.title("📚 RAG 知识库平台")
    st.markdown(
        "在这里上传家电的《产品维修手册》、《常见故障排查指南》等文档。AI 售后专家会自动进行**语义切分**、**向量化**并**实时学习**。")
    st.divider()

    col_upload, col_tips = st.columns([2, 1])

    with col_upload:
        # 文件上传组件
        uploaded_file = st.file_uploader("请选择要上传的产品说明书文本 (.txt)", type=['txt'])

        if uploaded_file is not None:
            filename = uploaded_file.name
            st.success(f"✅ 已成功读取文件：{filename}")

            if st.button("开始向量化文档", type="primary", use_container_width=True):
                with st.spinner("后端正在切分语义块并进行大模型向量化，过程可能需要几十秒，请稍候..."):
                    try:
                        # 1. 读取文件内容
                        text_content = uploaded_file.read().decode('utf-8')

                        # 2. 发送给后端的 /api/chat/knowledge/upload 接口
                        payload = {
                            "text_data": text_content,
                            "filename": filename
                        }
                        # 注意这里的路径要和路由对齐
                        res = requests.post(f"{API_URL}/chat/knowledge/upload", json=payload)

                        if res.status_code == 200:
                            result_msg = res.json().get('msg')
                            st.balloons()  # 播放庆祝动画
                            st.success(f"🎉 知识库更新完成！系统反馈：{result_msg}")
                        else:
                            st.error(f"上传失败：{res.json().get('detail')}")

                    except Exception as e:
                        st.error(f"网络请求出错: {e}")

    with col_tips:
        st.info("💡 **向量化机制说明：**\n\n"
                "1. 上传的文本将首先进行 MD5 校验，防止重复计算浪费 Token。\n"
                "2. 超过阈值的长文本将触发 `SemanticChunker` 进行智能语义块切分。\n"
                "3. 向量化完成后，系统的 BM25 内存索引将被**热重载**，新知识立刻生效。")