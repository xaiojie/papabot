/**
   ST7789 SCL -> GPIO14
   ST7789 SDA -> GPIO13
   ST7789 RES -> GPIO2
   ST7789 DC  -> GPIO12
   ST7789 CS  -> GPIO15

   ENCODER A     -> GPIO5
   ENCODER B     -> GPIO4
   ENCODER PUSH  -> GPIO0

*/

#include <SPI.h>             // SPI驱动库
#include <Adafruit_GFX.h>    // TFT 绘图库
#include <Adafruit_ST7789.h> // TFT 驱动库

// 编码器引脚定义
const uint8_t Encoder_A_Pin = 5;
const uint8_t Encoder_B_Pin = 4;
const uint8_t Encoder_Push_Pin = 0;
// TFT引脚定义
const uint8_t TFT_SCL_Pin = 14;
const uint8_t TFT_SDA_Pin = 13;
const uint8_t TFT_RST_Pin = 16;
const uint8_t TFT_DC_Pin = 2;
const uint8_t TFT_CS_Pin = 15;

// 变量定义
char FormatString[10] = {0};     // 用于格式化字符串
int8_t Count = 0;                // 储存计数值
bool Need_Refresh_Screen = true; // 储存是否需要刷新屏幕

// 对象创建
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS_Pin, TFT_DC_Pin, TFT_RST_Pin); // 创建屏幕对象

void ICACHE_RAM_ATTR Encoder_Interrupt_Callback(void)
{
  static bool encoderCw1Level = false; // 储存编码器B引脚电平
  static bool encoderCw2Level = false; // 储存编码器A引脚电平
  static bool encoderStatus = false;   // 储存编码器状态
  if (!encoderStatus && digitalRead(Encoder_A_Pin) == LOW)
  {
    encoderCw1Level = digitalRead(Encoder_B_Pin);
    encoderStatus = true;
  }
  if (encoderStatus && digitalRead(Encoder_A_Pin) == HIGH)
  {
    encoderCw2Level = !digitalRead(Encoder_B_Pin);
    if (encoderCw1Level == true && encoderCw2Level == true)
    {
      if (Count < 100) // 如果计数值小于100
      {
        Count++;                    // 计数值增加
        Need_Refresh_Screen = true; // 记录需要刷新屏幕
      }
    }
    if (encoderCw1Level == false && encoderCw2Level == false)
    {
      if (Count > -100) // 如果计数值大于-100
      {
        Count--;                    // 计数值减少
        Need_Refresh_Screen = true; // 记录需要刷新屏幕
      }
    }
    encoderStatus = false;
  }
}
void setup(void)
{
  Serial.begin(115200);                                               // 初始化串口监视器
  tft.init(240, 320);                                                 // 初始化屏幕
  tft.setRotation(3);                                                 // 设置屏幕方向
  tft.fillScreen(ST77XX_BLACK);                                       // 屏幕填充黑色
  tft.setTextSize(3);                                                 // 设置字体大小
  tft.setTextColor(ST77XX_RED, ST77XX_BLACK);                         // 设置显示颜色
  tft.setCursor(61, 108);                                             // 设置显示位置
  tft.print("Count: ");                                               // 显示字符
  tft.print(Count);                                                   // 显示字符
  pinMode(Encoder_A_Pin, INPUT_PULLUP);                               // 设置按钮引脚为上拉输入
  pinMode(Encoder_B_Pin, INPUT_PULLUP);                               // 设置按钮引脚为上拉输入
  pinMode(Encoder_Push_Pin, INPUT_PULLUP);                            // 设置按钮引脚为上拉输入
  attachInterrupt(Encoder_A_Pin, Encoder_Interrupt_Callback, CHANGE); // 注册外部双边中断回调函数
}

void loop(void)
{
  if (Need_Refresh_Screen == true) // 如果需要刷新屏幕
  {
    Need_Refresh_Screen = false;                // 记录不需要刷新屏幕
    Serial.println("Count: ");                  // 打印计数值
    Serial.println(Count);                      // 打印计数值
    tft.setTextSize(3);                         // 设置字体大小
    tft.setTextColor(ST77XX_RED, ST77XX_BLACK); // 设置显示颜色
    tft.setCursor(187, 108);                    // 设置显示位置
    tft.print(Count);                           // 显示字符
    tft.print("    ");                          // 清空字符
  }

  if (digitalRead(Encoder_Push_Pin) == LOW) // 如果按钮按下
  {
    delay(10);                                // 延时10ms
    if (digitalRead(Encoder_Push_Pin) == LOW) // 如果按钮还是按下
    {
      if (Count != 0) // 如果计数值不为0
      {
        Count = 0;                  // 清空计数值
        Need_Refresh_Screen = true; // 记录需要刷新屏幕
      }
    }
  }
}
