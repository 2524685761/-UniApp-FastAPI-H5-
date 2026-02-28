<template>
	<view class="index-page">
		<!-- 自定义顶部导航栏 -->
		<view class="custom-navbar">
			<view class="navbar-content">
				<view class="navbar-left">
					<text class="app-logo">🎓</text>
					<text class="app-title">情感伴学</text>
				</view>
				<view class="navbar-right" @click="goSettings">
					<text class="settings-icon">⚙️</text>
				</view>
			</view>
		</view>

		<!-- 页面内容区（需要留出顶部和底部空间） -->
		<view class="page-content">
			<!-- 顶部用户信息区 -->
			<view class="header-section">
				<view class="user-row">
					<view class="greeting-box">
						<text class="greeting-emoji">👋</text>
						<view class="greeting-text">
							<text class="greeting-main">Hi, 小朋友!</text>
							<text class="greeting-sub">今天想去哪里探险？</text>
						</view>
					</view>
					<view class="star-badge" @click="switchToProfile">
						<text class="star-icon">⭐</text>
						<text class="star-count">{{ userStars }}</text>
					</view>
				</view>
				
				<!-- 今日目标卡片 -->
				<view class="daily-goal-card">
					<view class="goal-icon">🎯</view>
					<view class="goal-content">
						<text class="goal-title">今日目标</text>
						<text class="goal-desc">完成 3 个关卡，获得更多星星！</text>
					</view>
					<view class="goal-progress">
						<view class="progress-circle">
							<text class="progress-num">{{ completedToday }}/3</text>
						</view>
					</view>
				</view>
			</view>
			
			<!-- 快捷入口 -->
			<view class="quick-actions">
				<view class="quick-btn chat" @click="switchToChat">
					<text class="quick-icon">🤖</text>
					<text class="quick-text">AI小伙伴</text>
				</view>
				<view class="quick-btn vocab" @click="goVocabBook">
					<text class="quick-icon">📚</text>
					<text class="quick-text">生词本</text>
				</view>
				<view class="quick-btn profile" @click="switchToProfile">
					<text class="quick-icon">👤</text>
					<text class="quick-text">我的</text>
				</view>
			</view>

			<!-- 关卡地图标题 -->
			<view class="section-header">
				<text class="section-title">🗺️ 学习关卡</text>
				<text class="section-hint">选择一个开始学习吧！</text>
			</view>

			<!-- 关卡网格 -->
			<view class="level-grid">
				<view 
					class="level-card" 
					v-for="(item, index) in courses" 
					:key="index"
					:class="['theme-' + ((index % 4) + 1)]"
					@click="startLearn(item)"
				>
					<!-- 关卡装饰 -->
					<view class="card-badge" v-if="index === 0">新手</view>
					<view class="card-badge hot" v-else-if="index === 1">热门</view>
					
					<!-- 关卡图标 -->
					<view class="level-icon-wrapper">
						<text class="level-icon">{{ getIcon(item.title) }}</text>
					</view>
					
					<!-- 关卡信息 -->
					<view class="level-info">
						<text class="level-title">{{ item.title }}</text>
						<text class="level-desc">{{ item.level || 'Level ' + (index + 1) }}</text>
					</view>
					
					<!-- GO按钮 -->
					<view class="go-btn">
						<text>GO!</text>
					</view>
				</view>
			</view>

			<!-- 空状态 -->
			<view class="empty-state" v-if="courses.length === 0 && !loading">
				<text class="empty-icon">📭</text>
				<text class="empty-text">暂无课程</text>
				<text class="empty-hint">请检查网络连接或稍后重试</text>
				<button class="retry-btn" @click="fetchCourses">重新加载</button>
			</view>

			<!-- 底部装饰 -->
			<view class="footer-decoration">
				<text>🌈 快乐学习，天天向上 🚀</text>
			</view>
		</view>

		<!-- 自定义底部TabBar -->
		<view class="custom-tabbar">
			<view class="tabbar-item active" @click="switchToIndex">
				<text class="tabbar-icon">📖</text>
				<text class="tabbar-text">学习</text>
			</view>
			<view class="tabbar-item" @click="switchToChat">
				<text class="tabbar-icon">🤖</text>
				<text class="tabbar-text">AI聊天</text>
			</view>
			<view class="tabbar-item" @click="switchToProfile">
				<text class="tabbar-icon">👤</text>
				<text class="tabbar-text">我的</text>
			</view>
		</view>
	</view>
</template>

<script>
	import { buildURL } from '../../utils/api.js'
	
	export default {
		data() {
			return {
				userStars: 0,
				courses: [],
				loading: false,
				completedToday: 0
			}
		},
		onShow() {
			this.userStars = uni.getStorageSync('user_stars') || 0
			this.completedToday = uni.getStorageSync('completed_today') || 0
			this.fetchCourses()
		},
		methods: {
			async fetchCourses() {
				this.loading = true
				uni.request({
					url: buildURL('/courses'),
					success: (res) => {
						if (res.statusCode === 200) {
							this.courses = res.data
						}
					},
					fail: () => {
						uni.showToast({ 
							title: '后端未连接，请到【我的】里设置后端地址', 
							icon: 'none', 
							duration: 2500 
						})
						// 离线模拟数据
						this.courses = [
							{ id: 1, title: '基础问候 👋', level: 'Level 1 · 入门', content_json: '[]' },
							{ id: 2, title: '校园生活 🏫', level: 'Level 2 · 进阶', content_json: '[]' },
							{ id: 3, title: '情感表达 😊', level: 'Level 3 · 提高', content_json: '[]' },
							{ id: 4, title: '动物世界 🐼', level: 'Level 4 · 拓展', content_json: '[]' }
						]
					},
					complete: () => {
						this.loading = false
					}
				})
			},
			startLearn(course) {
				try {
					uni.setStorageSync('current_course_content', JSON.parse(course.content_json))
				} catch (e) {
					uni.setStorageSync('current_course_content', [])
				}
				uni.navigateTo({
					url: `/pages/learn/learn?id=${course.id}&title=${course.title}`
				})
			},
			// TabBar 切换方法 - 使用 switchTab
			switchToIndex() {
				// 当前页面，不需要跳转
			},
			switchToChat() {
				uni.switchTab({ url: '/pages/chat/chat' })
			},
			switchToProfile() {
				uni.switchTab({ url: '/pages/profile/profile' })
			},
			// 普通页面跳转 - 使用 navigateTo
			goVocabBook() {
				uni.navigateTo({ url: '/pages/vocabbook/vocabbook' })
			},
			goSettings() {
				uni.navigateTo({ url: '/pages/settings/settings' })
			},
			getIcon(title) {
				// 主题字库 emoji 映射
				const emojiPatterns = ['🐾', '👤', '👕', '🎨', '🍎', '🍊', '🪑', '👔', '🚗', '☀️']
				for (const emoji of emojiPatterns) {
					if (title.includes(emoji)) return emoji
				}

				if (title.includes('问候')) return '👋'
				if (title.includes('校园')) return '🏫'
				if (title.includes('情感')) return '😊'
				if (title.includes('动物')) return '🐼'
				if (title.includes('水果')) return '🍎'
				if (title.includes('蔬菜')) return '🥕'
				if (title.includes('颜色')) return '🎨'
				if (title.includes('数字')) return '🔢'
				if (title.includes('身体')) return '💪'
				if (title.includes('家庭')) return '👨‍👩‍👧'
				return '📚'
			}
		}
	}
</script>

<style>
	/* ========== 页面容器 ========== */
	.index-page {
		min-height: 100vh;
		background: linear-gradient(180deg, #FFF5E6 0%, #FFECD2 100%);
		display: flex;
		flex-direction: column;
	}

	/* ========== 自定义顶部导航栏 ========== */
	.custom-navbar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 999;
		background: linear-gradient(145deg, #FF9F43, #E17055);
		padding-top: constant(safe-area-inset-top);
		padding-top: env(safe-area-inset-top);
	}
	
	.navbar-content {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 24rpx 32rpx;
	}
	
	.navbar-left {
		display: flex;
		align-items: center;
		gap: 12rpx;
	}
	
	.app-logo {
		font-size: 44rpx;
	}
	
	.app-title {
		font-size: 36rpx;
		font-weight: bold;
		color: #FFF;
		text-shadow: 0 2rpx 4rpx rgba(0, 0, 0, 0.2);
	}
	
	.navbar-right {
		width: 72rpx;
		height: 72rpx;
		background: rgba(255, 255, 255, 0.2);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	
	.settings-icon {
		font-size: 36rpx;
	}

	/* ========== 页面内容区 ========== */
	.page-content {
		flex: 1;
		padding-top: calc(constant(safe-area-inset-top) + 100rpx);
		padding-top: calc(env(safe-area-inset-top) + 100rpx);
		padding-bottom: 180rpx;
	}

	/* ========== 顶部用户区 ========== */
	.header-section {
		padding: 24rpx 32rpx;
	}
	
	.user-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 24rpx;
	}
	
	.greeting-box {
		display: flex;
		align-items: center;
		gap: 16rpx;
	}
	
	.greeting-emoji {
		font-size: 56rpx;
		animation: wave 1.5s ease-in-out infinite;
	}
	
	@keyframes wave {
		0%, 100% { transform: rotate(0deg); }
		25% { transform: rotate(20deg); }
		75% { transform: rotate(-10deg); }
	}
	
	.greeting-text {
		display: flex;
		flex-direction: column;
	}
	
	.greeting-main {
		font-size: 40rpx;
		font-weight: 900;
		color: #2D3436;
	}
	
	.greeting-sub {
		font-size: 26rpx;
		color: #636E72;
		margin-top: 4rpx;
	}
	
	.star-badge {
		display: flex;
		align-items: center;
		gap: 8rpx;
		background: linear-gradient(145deg, #FFE082, #FFD54F);
		padding: 14rpx 28rpx;
		border-radius: 40rpx;
		box-shadow: 0 6rpx 0 #FFA000, 0 8rpx 20rpx rgba(255, 193, 7, 0.3);
		transition: all 0.2s;
	}
	
	.star-badge:active {
		transform: translateY(4rpx);
		box-shadow: 0 2rpx 0 #FFA000;
	}
	
	.star-icon {
		font-size: 32rpx;
	}
	
	.star-count {
		font-size: 32rpx;
		font-weight: bold;
		color: #E65100;
	}

	/* ========== 今日目标卡片 ========== */
	.daily-goal-card {
		display: flex;
		align-items: center;
		gap: 20rpx;
		background: #FFF;
		padding: 24rpx;
		border-radius: 28rpx;
		box-shadow: 0 8rpx 24rpx rgba(255, 159, 67, 0.15);
	}
	
	.goal-icon {
		font-size: 48rpx;
	}
	
	.goal-content {
		flex: 1;
	}
	
	.goal-title {
		font-size: 28rpx;
		font-weight: bold;
		color: #2D3436;
		display: block;
	}
	
	.goal-desc {
		font-size: 24rpx;
		color: #636E72;
		margin-top: 4rpx;
	}
	
	.progress-circle {
		width: 80rpx;
		height: 80rpx;
		border-radius: 50%;
		background: linear-gradient(145deg, #55EFC4, #00B894);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	
	.progress-num {
		font-size: 24rpx;
		font-weight: bold;
		color: #FFF;
	}

	/* ========== 快捷入口 ========== */
	.quick-actions {
		display: flex;
		justify-content: center;
		gap: 24rpx;
		padding: 24rpx 32rpx;
	}
	
	.quick-btn {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8rpx;
		padding: 20rpx 28rpx;
		background: #FFF;
		border-radius: 24rpx;
		box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.06);
		transition: all 0.2s;
		min-width: 140rpx;
	}
	
	.quick-btn:active {
		transform: scale(0.96);
	}
	
	.quick-btn.chat {
		background: linear-gradient(145deg, #E3F2FD, #BBDEFB);
	}
	
	.quick-btn.vocab {
		background: linear-gradient(145deg, #F3E5F5, #E1BEE7);
	}
	
	.quick-btn.profile {
		background: linear-gradient(145deg, #E8F5E9, #C8E6C9);
	}
	
	.quick-icon {
		font-size: 40rpx;
	}
	
	.quick-text {
		font-size: 24rpx;
		font-weight: 600;
		color: #2D3436;
	}

	/* ========== 关卡标题 ========== */
	.section-header {
		padding: 16rpx 32rpx;
	}
	
	.section-title {
		font-size: 36rpx;
		font-weight: bold;
		color: #2D3436;
		display: block;
	}
	
	.section-hint {
		font-size: 24rpx;
		color: #636E72;
		margin-top: 4rpx;
	}

	/* ========== 关卡网格 ========== */
	.level-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 24rpx;
		padding: 8rpx 32rpx;
	}
	
	.level-card {
		background: #FFF;
		border-radius: 32rpx;
		padding: 28rpx 20rpx;
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		position: relative;
		box-shadow: 0 8rpx 0 rgba(0, 0, 0, 0.06);
		border: 3rpx solid transparent;
		transition: all 0.2s;
		overflow: hidden;
	}
	
	.level-card:active {
		transform: translateY(6rpx);
		box-shadow: 0 2rpx 0 rgba(0, 0, 0, 0.06);
	}
	
	/* 主题配色 */
	.level-card.theme-1 {
		background: linear-gradient(180deg, #E3F2FD 0%, #FFF 100%);
		border-color: #90CAF9;
	}
	
	.level-card.theme-2 {
		background: linear-gradient(180deg, #FCE4EC 0%, #FFF 100%);
		border-color: #F48FB1;
	}
	
	.level-card.theme-3 {
		background: linear-gradient(180deg, #E8F5E9 0%, #FFF 100%);
		border-color: #A5D6A7;
	}
	
	.level-card.theme-4 {
		background: linear-gradient(180deg, #FFF3E0 0%, #FFF 100%);
		border-color: #FFCC80;
	}
	
	.card-badge {
		position: absolute;
		top: 16rpx;
		right: 16rpx;
		font-size: 20rpx;
		font-weight: bold;
		color: #FFF;
		background: linear-gradient(145deg, #55EFC4, #00B894);
		padding: 4rpx 14rpx;
		border-radius: 12rpx;
	}
	
	.card-badge.hot {
		background: linear-gradient(145deg, #FF7675, #D63031);
	}
	
	.level-icon-wrapper {
		width: 100rpx;
		height: 100rpx;
		background: rgba(255, 255, 255, 0.8);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 16rpx;
		box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);
	}
	
	.level-icon {
		font-size: 56rpx;
	}
	
	.level-info {
		display: flex;
		flex-direction: column;
		gap: 4rpx;
	}
	
	.level-title {
		font-size: 28rpx;
		font-weight: bold;
		color: #2D3436;
	}
	
	.level-desc {
		font-size: 22rpx;
		color: #636E72;
	}
	
	.go-btn {
		margin-top: 16rpx;
		background: linear-gradient(145deg, #FF9F43, #E17055);
		color: #FFF;
		font-size: 24rpx;
		font-weight: bold;
		padding: 10rpx 32rpx;
		border-radius: 20rpx;
		box-shadow: 0 4rpx 0 #C44A34;
	}

	/* ========== 空状态 ========== */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 80rpx 32rpx;
	}
	
	.empty-icon {
		font-size: 100rpx;
		margin-bottom: 24rpx;
	}
	
	.empty-text {
		font-size: 32rpx;
		font-weight: bold;
		color: #636E72;
	}
	
	.empty-hint {
		font-size: 26rpx;
		color: #B2BEC3;
		margin-top: 8rpx;
	}
	
	.retry-btn {
		margin-top: 32rpx;
		background: linear-gradient(145deg, #FF9F43, #E17055);
		color: #FFF;
		font-size: 28rpx;
		font-weight: bold;
		padding: 16rpx 48rpx;
		border-radius: 40rpx;
		border: none;
		box-shadow: 0 6rpx 0 #C44A34;
	}
	
	.retry-btn:active {
		transform: translateY(4rpx);
		box-shadow: 0 2rpx 0 #C44A34;
	}

	/* ========== 底部装饰 ========== */
	.footer-decoration {
		text-align: center;
		padding: 40rpx;
		font-size: 26rpx;
		color: #B2BEC3;
	}

	/* ========== 自定义底部TabBar ========== */
	.custom-tabbar {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		z-index: 999;
		display: flex;
		justify-content: space-around;
		align-items: center;
		height: 120rpx;
		background: #FFF;
		box-shadow: 0 -4rpx 20rpx rgba(0, 0, 0, 0.08);
		padding-bottom: constant(safe-area-inset-bottom);
		padding-bottom: env(safe-area-inset-bottom);
	}
	
	.tabbar-item {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 4rpx;
		padding: 12rpx 0;
		transition: all 0.2s;
	}
	
	.tabbar-item:active {
		transform: scale(0.95);
	}
	
	.tabbar-icon {
		font-size: 44rpx;
		transition: all 0.2s;
	}
	
	.tabbar-text {
		font-size: 22rpx;
		color: #636E72;
		font-weight: 500;
		transition: all 0.2s;
	}
	
	.tabbar-item.active .tabbar-icon {
		transform: scale(1.1);
	}
	
	.tabbar-item.active .tabbar-text {
		color: #FF9F43;
		font-weight: bold;
	}

	/* ========== 响应式适配 ========== */
	@media screen and (min-width: 768px) {
		.level-grid {
			grid-template-columns: repeat(3, 1fr);
			max-width: 800px;
			margin: 0 auto;
		}
	}
</style>
