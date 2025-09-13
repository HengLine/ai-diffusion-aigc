import streamlit as st
import os
from typing import List, Union, Optional

class CarouselComponent:
    """轮播组件，用于显示多张图片或视频，并提供下载功能"""
    
    @staticmethod
    def display_image_carousel(image_paths: List[str], caption: Optional[str] = None):
        """显示图像轮播组件"""
        if not image_paths or len(image_paths) == 0:
            return
        
        # 如果只有一张图片，直接显示
        if len(image_paths) == 1:
            image_path = image_paths[0]
            if os.path.exists(image_path):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.image(image_path, caption=caption or "生成结果", use_column_width=True)
                with col2:
                    CarouselComponent._add_download_button(image_path)
            return
        
        # 多张图片时显示轮播
        st.markdown("### 结果预览")
        
        # 创建轮播控制器
        if 'carousel_index' not in st.session_state:
            st.session_state.carousel_index = 0
            
        col1, col2, col3 = st.columns([1, 6, 1])
        
        with col1:
            if st.button("上一张", key="prev_btn"):
                st.session_state.carousel_index = (st.session_state.carousel_index - 1) % len(image_paths)
                
        with col3:
            if st.button("下一张", key="next_btn"):
                st.session_state.carousel_index = (st.session_state.carousel_index + 1) % len(image_paths)
                
        with col2:
            st.markdown(f"### 第 {st.session_state.carousel_index + 1}/{len(image_paths)} 张")
        
        # 显示当前图片
        current_image = image_paths[st.session_state.carousel_index]
        if os.path.exists(current_image):
            col_img, col_dl = st.columns([4, 1])
            with col_img:
                st.image(current_image, caption=caption or f"生成结果 #{st.session_state.carousel_index + 1}", use_column_width=True)
            with col_dl:
                CarouselComponent._add_download_button(current_image)
        
        # 显示缩略图导航
        CarouselComponent._display_thumbnails(image_paths)
    
    @staticmethod
    def display_video_carousel(video_paths: List[str], caption: Optional[str] = None):
        """显示视频轮播组件"""
        if not video_paths or len(video_paths) == 0:
            return
        
        # 如果只有一个视频，直接显示
        if len(video_paths) == 1:
            video_path = video_paths[0]
            if os.path.exists(video_path):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.video(video_path, format="video/mp4")
                with col2:
                    CarouselComponent._add_download_button(video_path)
            return
        
        # 多个视频时显示轮播
        st.markdown("### 结果预览")
        
        # 创建轮播控制器
        if 'video_carousel_index' not in st.session_state:
            st.session_state.video_carousel_index = 0
            
        col1, col2, col3 = st.columns([1, 6, 1])
        
        with col1:
            if st.button("上一个", key="prev_video_btn"):
                st.session_state.video_carousel_index = (st.session_state.video_carousel_index - 1) % len(video_paths)
                
        with col3:
            if st.button("下一个", key="next_video_btn"):
                st.session_state.video_carousel_index = (st.session_state.video_carousel_index + 1) % len(video_paths)
                
        with col2:
            st.markdown(f"### 第 {st.session_state.video_carousel_index + 1}/{len(video_paths)} 个")
        
        # 显示当前视频
        current_video = video_paths[st.session_state.video_carousel_index]
        if os.path.exists(current_video):
            col_vid, col_dl = st.columns([4, 1])
            with col_vid:
                st.video(current_video, format="video/mp4")
            with col_dl:
                CarouselComponent._add_download_button(current_video)
    
    @staticmethod
    def _display_thumbnails(image_paths: List[str]):
        """显示缩略图导航"""
        if len(image_paths) <= 1:
            return
        
        st.markdown("### 缩略图导航")
        
        # 计算每页显示的缩略图数量
        num_cols = min(4, len(image_paths))  # 最多4列
        cols = st.columns(num_cols)
        
        # 分页逻辑
        if 'thumbnail_page' not in st.session_state:
            st.session_state.thumbnail_page = 0
            
        total_pages = (len(image_paths) + num_cols - 1) // num_cols
        start_idx = st.session_state.thumbnail_page * num_cols
        end_idx = min(start_idx + num_cols, len(image_paths))
        
        # 显示当前页的缩略图
        for i, idx in enumerate(range(start_idx, end_idx)):
            with cols[i]:
                image_path = image_paths[idx]
                if os.path.exists(image_path):
                    # 显示缩略图
                    st.image(image_path, width=100)
                    # 添加选择按钮
                    if st.button(f"选择 #{idx + 1}", key=f"select_{idx}"):
                        st.session_state.carousel_index = idx
        
        # 显示分页控制
        if total_pages > 1:
            col_prev, col_page, col_next = st.columns([1, 2, 1])
            with col_prev:
                if st.button("上一页", key="prev_thumbnail_page"):
                    if st.session_state.thumbnail_page > 0:
                        st.session_state.thumbnail_page -= 1
            with col_page:
                st.markdown(f"页码: {st.session_state.thumbnail_page + 1}/{total_pages}")
            with col_next:
                if st.button("下一页", key="next_thumbnail_page"):
                    if st.session_state.thumbnail_page < total_pages - 1:
                        st.session_state.thumbnail_page += 1
    
    @staticmethod
    def _add_download_button(file_path: str):
        """添加下载按钮"""
        if not os.path.exists(file_path):
            return
        
        try:
            # 读取文件内容
            with open(file_path, "rb") as file:
                file_bytes = file.read()
            
            # 获取文件名
            file_name = os.path.basename(file_path)
            
            # 添加下载按钮
            st.download_button(
                label="下载",
                data=file_bytes,
                file_name=file_name,
                mime="application/octet-stream"
            )
        except Exception as e:
            st.error(f"无法提供下载: {str(e)}")