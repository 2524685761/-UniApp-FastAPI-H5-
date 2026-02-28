<script>
	export default {
		onLaunch: function() {
			console.log('App Launch')
			// 初始化星星数量
			if (!uni.getStorageSync('user_stars')) {
				uni.setStorageSync('user_stars', 0)
			}
		}
	}
</script>

<style>
	/* ========== 全局CSS变量 - 幼儿教育温馨配色方案 ========== */
	page {
		/* 主色调 - 温暖阳光橙 */
		--primary-color: #FF9F43;
		--primary-light: #FFEAA7;
		--primary-dark: #E17055;
		
		/* 辅助色 - 清新青绿 */
		--accent-color: #00CEC9;
		--accent-light: #81ECEC;
		--accent-dark: #00B894;
		
		/* 成功色 - 柔和绿 */
		--success-color: #55EFC4;
		--success-light: #E8F8F5;
		--success-dark: #00B894;
		
		/* 警告色 - 温和橙 */
		--warning-color: #FDCB6E;
		--warning-light: #FFF9E6;
		--warning-dark: #F39C12;
		
		/* 错误色 - 柔和红 */
		--error-color: #FF7675;
		--error-light: #FFEBE9;
		--error-dark: #D63031;
		
		/* 文字颜色 */
		--text-primary: #2D3436;
		--text-secondary: #636E72;
		--text-hint: #B2BEC3;
		--text-white: #FFFFFF;
		
		/* 背景色 */
		--bg-primary: #FFF9F0;
		--bg-secondary: #F8F9FA;
		--bg-card: #FFFFFF;
		--bg-mask: rgba(0, 0, 0, 0.4);
		
		/* 边框和阴影 */
		--border-light: rgba(0, 0, 0, 0.06);
		--border-normal: rgba(0, 0, 0, 0.1);
		--shadow-sm: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);
		--shadow-md: 0 8rpx 24rpx rgba(0, 0, 0, 0.12);
		--shadow-lg: 0 16rpx 48rpx rgba(0, 0, 0, 0.16);
		--shadow-cartoon: 0 8rpx 0 rgba(0, 0, 0, 0.08);
		
		/* 圆角 */
		--radius-sm: 16rpx;
		--radius-md: 24rpx;
		--radius-lg: 36rpx;
		--radius-xl: 48rpx;
		--radius-full: 1000rpx;
		
		/* 间距 */
		--spacing-xs: 8rpx;
		--spacing-sm: 16rpx;
		--spacing-md: 24rpx;
		--spacing-lg: 32rpx;
		--spacing-xl: 48rpx;
		
		/* 字体大小 */
		--font-xs: 22rpx;
		--font-sm: 26rpx;
		--font-md: 30rpx;
		--font-lg: 36rpx;
		--font-xl: 44rpx;
		--font-xxl: 56rpx;
		--font-giant: 80rpx;
		
		/* 动画时长 */
		--transition-fast: 0.15s;
		--transition-normal: 0.25s;
		--transition-slow: 0.4s;
		
		/* 触摸区域最小尺寸 (无障碍标准 44px ≈ 88rpx) */
		--touch-min: 88rpx;
		
		/* 页面基础样式 */
		background-color: var(--bg-primary);
		font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", sans-serif;
		color: var(--text-primary);
		font-size: var(--font-md);
		line-height: 1.6;
	}

	/* ========== 全局容器 ========== */
	.container {
		padding: var(--spacing-lg);
		min-height: 100vh;
		box-sizing: border-box;
	}

	/* ========== 卡通卡片风格 ========== */
	.card {
		background: var(--bg-card);
		border-radius: var(--radius-lg);
		padding: var(--spacing-lg);
		margin-bottom: var(--spacing-lg);
		box-shadow: var(--shadow-cartoon);
		transition: all var(--transition-fast);
		border: 2rpx solid var(--border-light);
	}
	
	.card:active {
		transform: translateY(4rpx);
		box-shadow: 0 4rpx 0 rgba(0, 0, 0, 0.08);
	}

	/* ========== 按钮风格 ========== */
	.btn-cartoon {
		background: linear-gradient(145deg, var(--primary-color), var(--primary-dark));
		color: var(--text-white);
		border-radius: var(--radius-full);
		padding: var(--spacing-md) var(--spacing-xl);
		text-align: center;
		font-size: var(--font-lg);
		font-weight: bold;
		box-shadow: 0 8rpx 0 var(--primary-dark), var(--shadow-md);
		border: none;
		transition: all var(--transition-fast);
		min-height: var(--touch-min);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	
	.btn-cartoon:active {
		transform: translateY(6rpx);
		box-shadow: 0 2rpx 0 var(--primary-dark);
	}
	
	.btn-secondary {
		background: linear-gradient(145deg, var(--accent-color), var(--accent-dark));
		box-shadow: 0 8rpx 0 var(--accent-dark), var(--shadow-md);
	}
	
	.btn-secondary:active {
		box-shadow: 0 2rpx 0 var(--accent-dark);
	}
	
	.btn-outline {
		background: var(--bg-card);
		color: var(--primary-color);
		border: 3rpx solid var(--primary-color);
		box-shadow: var(--shadow-sm);
	}
	
	.btn-outline:active {
		background: var(--primary-light);
	}

	/* ========== 标题风格 ========== */
	.cartoon-title {
		font-size: var(--font-xxl);
		font-weight: 900;
		color: var(--text-primary);
		text-shadow: 2rpx 2rpx 0 #fff;
		margin-bottom: var(--spacing-md);
	}
	
	.section-title {
		font-size: var(--font-lg);
		font-weight: bold;
		color: var(--text-primary);
		margin: var(--spacing-lg) 0 var(--spacing-md);
		padding-left: var(--spacing-sm);
		border-left: 6rpx solid var(--primary-color);
	}

	/* ========== 动画定义 ========== */
	@keyframes bounce {
		0%, 100% { transform: translateY(0); }
		50% { transform: translateY(-12rpx); }
	}
	
	@keyframes pulse {
		0%, 100% { transform: scale(1); }
		50% { transform: scale(1.05); }
	}
	
	@keyframes shake {
		0%, 100% { transform: translateX(0); }
		20% { transform: translateX(-10rpx); }
		40% { transform: translateX(10rpx); }
		60% { transform: translateX(-10rpx); }
		80% { transform: translateX(10rpx); }
	}
	
	@keyframes fadeIn {
		from { opacity: 0; transform: translateY(20rpx); }
		to { opacity: 1; transform: translateY(0); }
	}
	
	@keyframes glow {
		0%, 100% { box-shadow: 0 0 20rpx rgba(255, 159, 67, 0.4); }
		50% { box-shadow: 0 0 40rpx rgba(255, 159, 67, 0.8); }
	}
	
	@keyframes ripple {
		to { transform: scale(2); opacity: 0; }
	}
	
	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}
	
	/* ========== 加载状态 ========== */
	.loading-spinner {
		width: 48rpx;
		height: 48rpx;
		border: 4rpx solid var(--border-light);
		border-top-color: var(--primary-color);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	/* ========== 安全区域适配 ========== */
	.safe-area-bottom {
		padding-bottom: constant(safe-area-inset-bottom);
		padding-bottom: env(safe-area-inset-bottom);
	}
	
	.safe-area-top {
		padding-top: constant(safe-area-inset-top);
		padding-top: env(safe-area-inset-top);
	}
</style>
