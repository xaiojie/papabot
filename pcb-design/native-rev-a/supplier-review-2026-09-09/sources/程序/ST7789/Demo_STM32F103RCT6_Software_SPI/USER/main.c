//////////////////////////////////////////////////////////////////////////////////	 
//本程序只供学习使用，未经作者许可，不得用于其它任何用途
//  功能描述   : 2.4寸LCD 4接口演示例程(STM32系列)
//               EC11旋转编码器旋转选择测试的内容
/******************************************************************************
//本程序适用与STM32F103C8
//              GND   电源地
//              VCC   接5V或3.3v电源
//              SCL   接PA4（SCL）
//              SDA   接PA5（SDA）
//              RES   接PA6
//              DC    接PA7
//              CS    接PA8
//							BL		接PA9
//							A    接PA0
//							B    接PA1
//							PUSH    接PA2
//							K0    接PA3
*******************************************************************************/
#include "delay.h"
#include "sys.h"
#include "lcd.h"
#include "touch.h"
#include "gui.h"
#include "test.h"
#include "stm32f10x_gpio.h"
#include "stm32f10x_exti.h"
#include "misc.h"
#include "stm32f10x.h"

extern unsigned char key_count;
extern unsigned char edit;
extern unsigned char first_in;
int count=0;

void EXTI_ABInit(void)
{
	GPIO_InitTypeDef GPIO_InitStructure;
  EXTI_InitTypeDef EXTI_InitStructure;
	NVIC_InitTypeDef NVIC_InitStructure;
	
	
	/* 开启GPIO时钟 */
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_AFIO,ENABLE);
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA,ENABLE);

	GPIO_InitStructure.GPIO_Pin=GPIO_Pin_0 |GPIO_Pin_1 | GPIO_Pin_2 | GPIO_Pin_3;
	GPIO_InitStructure.GPIO_Mode=GPIO_Mode_IN_FLOATING;
	GPIO_InitStructure.GPIO_Speed=GPIO_Speed_50MHz;
	GPIO_Init(GPIOA,&GPIO_InitStructure);
	 

	NVIC_InitStructure.NVIC_IRQChannel = EXTI0_IRQn; 
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 0x02; 
	NVIC_InitStructure.NVIC_IRQChannelSubPriority = 0; 
	NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE; 
	NVIC_Init(&NVIC_InitStructure); 
	
	NVIC_InitStructure.NVIC_IRQChannel = EXTI1_IRQn; 
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 0x02; 
	NVIC_InitStructure.NVIC_IRQChannelSubPriority = 0; 
	NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE; 
	NVIC_Init(&NVIC_InitStructure); 
	
	NVIC_InitStructure.NVIC_IRQChannel = EXTI2_IRQn; 
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 0x02; 
	NVIC_InitStructure.NVIC_IRQChannelSubPriority = 0; 
	NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE; 
	NVIC_Init(&NVIC_InitStructure); 
	
	NVIC_InitStructure.NVIC_IRQChannel = EXTI3_IRQn; 
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 0x02; 
	NVIC_InitStructure.NVIC_IRQChannelSubPriority = 0; 
	NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE; 
	NVIC_Init(&NVIC_InitStructure); 
	


       //??????PC.2 PC.3 PC.5
				GPIO_EXTILineConfig(GPIO_PortSourceGPIOA,GPIO_PinSource0);
       GPIO_EXTILineConfig(GPIO_PortSourceGPIOA,GPIO_PinSource1);

       GPIO_EXTILineConfig(GPIO_PortSourceGPIOA,GPIO_PinSource2);

       GPIO_EXTILineConfig(GPIO_PortSourceGPIOA,GPIO_PinSource3);
 

       EXTI_InitStructure.EXTI_Line= EXTI_Line0 |EXTI_Line1 | EXTI_Line2 | EXTI_Line3; //??????2 3 5

       EXTI_InitStructure.EXTI_Mode= EXTI_Mode_Interrupt; //???????,?????

       EXTI_InitStructure.EXTI_Trigger= EXTI_Trigger_Falling; //???????????????

       EXTI_InitStructure.EXTI_LineCmd=ENABLE;                                          //??????

      EXTI_Init(&EXTI_InitStructure);
 
}
 
void EXTI0_IRQHandler(void) 
{ 
	if(EXTI_GetITStatus(EXTI_Line0) != RESET) 
	{
		delay_ms(2);
		if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_0)==0
			&&GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_1)==1)
		{
				key_count++;
				if(key_count>4)
				{
					key_count=1;
				}
				
				count++;
		}
			EXTI_ClearITPendingBit(EXTI_Line0);
	}
	
}
 
void EXTI1_IRQHandler(void) 
{ 
  if(EXTI_GetITStatus(EXTI_Line1) != RESET) 
	{
		delay_ms(2);
		if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_1)==0
			&&GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_0)==1)
		{
				key_count--;
				if(key_count<1)
				{
					key_count=4;
				}
				count--;
		}
		
    EXTI_ClearITPendingBit(EXTI_Line1);
	}
}

void EXTI2_IRQHandler(void) 
{ 
	if(EXTI_GetITStatus(EXTI_Line2) != RESET) 
	{
		delay_ms(2);
		if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_2)==0)
		{
		edit=1;
    
		count=0;
		}
	}
	EXTI_ClearITPendingBit(EXTI_Line2);
}
 
void EXTI3_IRQHandler(void) 
{ 
  if(EXTI_GetITStatus(EXTI_Line3) != RESET) 
	{
		delay_ms(2);
		if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_3)==0)
		{
		edit=0;
		first_in=0;
		}
	}
	EXTI_ClearITPendingBit(EXTI_Line3);
}

int main(void)
{	
	SystemInit();//初始化RCC 设置系统主频为72MHZ
	delay_init(72);	     //延时初始化
	LCD_Init();	   //液晶屏初始化
	EXTI_ABInit();
	//注意，需要接入旋转编码器，才能正常工作，不然菜单页会乱跳
	while(1)
  {  
		QDTFT_Test_Demo();	//See the test details in QDTFT_Demo.c	
		
  }

}

