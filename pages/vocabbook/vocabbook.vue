<template>
	<view class="vocabbook-page">
		<!-- 自定义顶部导航栏 -->
		<view class="custom-navbar">
			<view class="navbar-content">
				<view class="navbar-left" @click="goBack">
					<text class="back-icon">←</text>
				</view>
				<view class="navbar-center">
					<text class="navbar-title">📚 我的生词本</text>
				</view>
				<view class="navbar-right">
					<view class="word-count-badge" v-if="items.length > 0">
						<text>{{ items.length }}</text>
					</view>
				</view>
			</view>
		</view>

		<!-- 页面内容区 -->
		<view class="page-content">

		<!-- 加载状态 -->
		<view class="loading-card" v-if="loading">
			<view class="loading-spinner"></view>
			<text class="loading-text">加载中...</text>
		</view>

		<!-- 空状态 -->
		<view class="empty-card" v-else-if="!items.length">
			<text class="empty-icon">📭</text>
			<text class="empty-title">暂无生词</text>
			<text class="empty-hint">去学习页多练几次，低分词会自动出现在这里～</text>
			<button class="go-learn-btn" @click="goLearn">
				<text class="btn-icon">🎯</text>
				<text>去学习</text>
			</button>
		</view>

		<!-- 生词列表 -->
		<view class="word-list" v-else>
			<view 
				class="word-card" 
				v-for="(it, idx) in items" 
				:key="idx"
				@click="practice(it)"
			>
				<view class="word-main">
					<view class="word-content">
						<text class="word-hanzi">{{ it.word_text }}</text>
						<text class="word-pinyin">{{ it.pinyin || '' }}</text>
					</view>
					<view class="word-stats">
						<view class="stat-item">
							<text class="stat-icon">⭐</text>
							<text class="stat-value">{{ it.avg_score }}</text>
							<text class="stat-unit">分</text>
						</view>
						<view class="stat-divider"></view>
						<view class="stat-item">
							<text class="stat-icon">🔄</text>
							<text class="stat-value">{{ it.times }}</text>
							<text class="stat-unit">次</text>
						</view>
					</view>
				</view>
				<view class="practice-btn">
					<text class="practice-icon">▶</text>
				</view>
			</view>
		</view>

		<!-- 底部提示 -->
		<view class="footer-tip" v-if="items.length > 0">
			<text class="tip-icon">💡</text>
			<text class="tip-text">点击词卡可以直接开始练习</text>
		</view>
		</view>
	</view>
</template>

<script>
	import { buildURL, getUserId } from '../../utils/api.js'
	
	export default {
		data() {
			return {
				loading: true,
				items: [],
				practiceCourseId: null
			}
		},
		onShow() {
			this.fetchCourseId()
			this.fetchWeakWords()
		},
		methods: {
			goBack() {
				uni.navigateBack()
			},
			goLearn() {
				uni.switchTab({ url: '/pages/index/index' })
			},
			fetchCourseId() {
				uni.request({
					url: buildURL('/vocabbook/course'),
					success: (res) => {
						if (res.statusCode === 200 && res.data && res.data.id) {
							this.practiceCourseId = res.data.id
						}
					}
				})
			},
			fetchWeakWords() {
				this.loading = true
				uni.request({
					url: buildURL(`/weak_words?user_id=${getUserId()}&limit=50`),
					success: (res) => {
						if (res.statusCode === 200 && Array.isArray(res.data)) {
							this.items = res.data
						} else {
							this.items = []
						}
					},
					fail: () => {
						this.items = []
						uni.showToast({ 
							title: '后端未连接，请先到设置页测试连接', 
							icon: 'none', 
							duration: 2500 
						})
					},
					complete: () => {
						this.loading = false
					}
				})
			},
			practice(it) {
				const content = [{
					text: it.word_text,
					pinyin: it.pinyin || '',
					tip: '这是你的薄弱词：先听示范，再慢慢读。'
				}]
				uni.setStorageSync('current_course_content', content)
				const id = this.practiceCourseId || 1
				uni.navigateTo({ url: `/pages/learn/learn?id=${id}&title=生词本` })
			}
		}
	}
</script>

<style>
	/* ========== 页面容器 ========== */
	.vocabbook-page {
		min-height: 100vh;
		background: linear-gradient(180deg, #F3E5F5 0%, #EDE7F6 100%);
	}

	/* ========== 自定义顶部导航栏 ========== */
	.custom-navbar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 999;
		background: linear-gradient(145deg, #9B59B6, #8E44AD);
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
		width: 72rpx;
		height: 72rpx;
		background: rgba(255, 255, 255, 0.2);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	
	.back-icon {
		font-size: 36rpx;
		color: #FFF;
	}
	
	.navbar-center {
		flex: 1;
		text-align: center;
	}
	
	.navbar-title {
		font-size: 34rpx;
		font-weight: bold;
		color: #FFF;
	}
	
	.navbar-right {
		width: 72rpx;
		display: flex;
		justify-content: flex-end;
	}
	
	.word-count-badge {
		background: rgba(255, 255, 255, 0.3);
		padding: 8rpx 20rpx;
		border-radius: 20rpx;
	}
	
	.word-count-badge text {
		font-size: 26rpx;
		font-weight: bold;
		color: #FFF;
	}

	/* ========== 页面内容区 ========== */
	.page-content {
		padding: 32rpx;
		padding-top: calc(constant(safe-area-inset-top) + 120rpx);
		padding-top: calc(env(safe-area-inset-top) + 120rpx);
		padding-bottom: 60rpx;
	}

	/* ========== 加载状态 ========== */
	.loading-card {
		background: #FFF;
		border-radius: 28rpx;
		padding: 80rpx;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 24rpx;
		box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.06);
	}
	
	.loading-spinner {
		width: 64rpx;
		height: 64rpx;
		border: 6rpx solid rgba(155, 89, 182, 0.2);
		border-top-color: #9B59B6;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	
	.loading-text {
		font-size: 28rpx;
		color: #636E72;
	}

	/* ========== 空状态 ========== */
	.empty-card {
		background: #FFF;
		border-radius: 28rpx;
		padding: 80rpx 48rpx;
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.06);
	}
	
	.empty-icon {
		font-size: 100rpx;
		margin-bottom: 24rpx;
	}
	
	.empty-title {
		font-size: 32rpx;
		font-weight: bold;
		color: #2D3436;
	}
	
	.empty-hint {
		font-size: 26rpx;
		color: #636E72;
		margin-top: 12rpx;
		line-height: 1.6;
	}
	
	.go-learn-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12rpx;
		margin-top: 32rpx;
		background: linear-gradient(145deg, #9B59B6, #8E44AD);
		color: #FFF;
		font-size: 30rpx;
		font-weight: bold;
		padding: 20rpx 48rpx;
		border-radius: 40rpx;
		border: none;
		box-shadow: 0 6rpx 0 #6C3483;
	}
	
	.go-learn-btn:active {
		transform: translateY(4rpx);
		box-shadow: 0 2rpx 0 #6C3483;
	}

	/* ========== 生词列表 ========== */
	.word-list {
		display: flex;
		flex-direction: column;
		gap: 20rpx;
	}
	
	.word-card {
		background: #FFF;
		border-radius: 24rpx;
		padding: 24rpx;
		display: flex;
		align-items: center;
		gap: 20rpx;
		box-shadow: 0 6rpx 20rpx rgba(0, 0, 0, 0.06);
		transition: all 0.2s;
	}
	
	.word-card:active {
		transform: scale(0.98);
		background: #FAFAFA;
	}
	
	.word-main {
		flex: 1;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	
	.word-content {
		display: flex;
		flex-direction: column;
	}
	
	.word-hanzi {
		font-size: 56rpx;
		font-weight: 900;
		color: #2D3436;
		line-height: 1.2;
	}
	
	.word-pinyin {
		font-size: 26rpx;
		color: #636E72;
		margin-top: 4rpx;
	}
	
	.word-stats {
		display: flex;
		align-items: center;
		gap: 16rpx;
	}
	
	.stat-item {
		display: flex;
		align-items: baseline;
		gap: 4rpx;
	}
	
	.stat-icon {
		font-size: 24rpx;
		margin-right: 4rpx;
	}
	
	.stat-value {
		font-size: 28rpx;
		font-weight: bold;
		color: #2D3436;
	}
	
	.stat-unit {
		font-size: 22rpx;
		color: #636E72;
	}
	
	.stat-divider {
		width: 2rpx;
		height: 24rpx;
		background: #E0E0E0;
	}
	
	.practice-btn {
		width: 72rpx;
		height: 72rpx;
		background: linear-gradient(145deg, #9B59B6, #8E44AD);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 6rpx 16rpx rgba(155, 89, 182, 0.4);
	}
	
	.practice-icon {
		font-size: 28rpx;
		color: #FFF;
		margin-left: 4rpx;
	}

	/* ========== 底部提示 ========== */
	.footer-tip {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8rpx;
		margin-top: 32rpx;
		padding: 16rpx;
	}
	
	.tip-icon {
		font-size: 24rpx;
	}
	
	.tip-text {
		font-size: 24rpx;
		color: #636E72;
	}

	/* ========== 动画 ========== */
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
